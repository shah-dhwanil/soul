"""Async detection worker. Never log message content."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent.config import Settings
from agent.model.detectors import DETECTORS
from agent.model.structured import async_structured_call, make_structured_llm
from agent.pg.models import Conversation, TraitStatus
from agent.policy.leanings import observe_leaning
from agent.policy.traits import observe_trait, trait_is_sensitive, trial_allowed
from agent.repositories.persona import DetectionJobRepository, PersonaRepository

logger = logging.getLogger(__name__)

DETECTION_BACKOFF_SECONDS = (1, 5, 30, 120, 600)
DETECTOR_NAMES = (
    "trust",
    "dependency",
    "trait_candidate",
    "trait_reaction",
    "leaning",
    "attunement",
)
_FAILED = object()  # sentinel returned by _run_detector on internal failure
_SHORT_EXPIRY_SIGNALS = frozenset({"d1", "d6"})
_SHORT_EXPIRY = timedelta(days=21)
_LONG_EXPIRY = timedelta(days=42)


@dataclass(frozen=True)
class DetectionWork:
    id: UUID
    user_id: str
    conversation_id: UUID
    user_message: str
    assistant_reply: str
    trait_used: str | None
    asked_question: bool
    mode: str
    enqueued_at: datetime


class DetectionWorker:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        llm: Any | None = None,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._llm = llm
        self._repo: PersonaRepository | None = None
        self._scheduler: AsyncIOScheduler | None = None
        self._poll_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if not self._settings.memory_ingest_enabled:
            logger.info("detection worker disabled")
            return
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._tick,
            "interval",
            seconds=max(1, int(self._settings.outbox_poll_interval_s)),
            id="detection_drain",
            replace_existing=True,
            max_instances=1,
        )
        self._scheduler.start()
        logger.info("detection worker started")

    async def stop(self) -> None:
        self._running = False
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        if self._poll_task is not None:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

    async def _tick(self) -> None:
        try:
            await self.drain_once()
        except Exception:
            logger.exception("detection worker tick error")

    async def _poll_loop(self) -> None:
        while self._running:
            await self._tick()
            await asyncio.sleep(self._settings.outbox_poll_interval_s)

    async def enqueue(self, work: DetectionWork) -> None:
        async with self._session_factory() as session:
            await DetectionJobRepository(session).enqueue(
                user_id=work.user_id, conversation_id=work.conversation_id
            )
            await session.commit()

    async def drain_once(self) -> bool:
        async with self._session_factory() as session:
            jobs = DetectionJobRepository(session)
            row = await jobs.claim_one()
            if row is None:
                return False
            try:
                conv = (
                    await session.execute(
                        select(Conversation).where(Conversation.id == row.conversation_id)
                    )
                ).scalar_one_or_none()
                if conv is None:
                    await jobs.mark_failed(row, "conversation_not_found")
                    await session.commit()
                    return False
                work = DetectionWork(
                    id=row.id,
                    user_id=row.user_id,
                    conversation_id=row.conversation_id,
                    user_message=conv.user_message,
                    assistant_reply=conv.agent_response,
                    trait_used=conv.trait_used,
                    asked_question=conv.asked_question,
                    mode=conv.mode or "everyday",
                    enqueued_at=row.created_at,
                )
                self._repo = PersonaRepository(session)
                failed = await self._process(work)
                if failed:
                    raise RuntimeError("detectors failed: " + ",".join(failed))
                await jobs.mark_processed(row)
                await session.commit()
                return True
            except Exception as exc:
                err = f"{type(exc).__name__}: {exc}"
                if row.attempts >= self._settings.outbox_max_attempts:
                    await jobs.mark_failed(row, err)
                else:
                    await jobs.requeue_for_retry(row, err)
                    await asyncio.sleep(
                        DETECTION_BACKOFF_SECONDS[
                            min(row.attempts - 1, len(DETECTION_BACKOFF_SECONDS) - 1)
                        ]
                    )
                await session.commit()
                logger.warning(
                    "detection failed job=%s user=%s error_type=%s",
                    row.id,
                    row.user_id,
                    type(exc).__name__,
                )
                return False
            finally:
                self._repo = None

    async def process(self, work: DetectionWork) -> None:
        """Run all detectors; never raises for a detector failure."""
        await self._process(work)

    async def _process(self, work: DetectionWork) -> list[str]:
        """Returns names of detectors that failed."""
        results: dict[str, Any] = {}
        failed: list[str] = []
        for name in DETECTOR_NAMES:
            try:
                out = await self._run_detector(name, work)
                if out is _FAILED:
                    failed.append(name)
                else:
                    results[name] = out
            except Exception as exc:  # noqa: BLE001
                failed.append(name)
                logger.warning(
                    "detector failed detector=%s error_type=%s",
                    name,
                    type(exc).__name__,
                )
        for name, result in results.items():
            if result is None:
                continue
            try:
                await self._apply(name, result, work)
            except Exception as exc:  # noqa: BLE001
                failed.append(name)
                logger.warning(
                    "detector apply failed detector=%s error_type=%s",
                    name,
                    type(exc).__name__,
                )
        return failed

    async def _run_detector(self, name: str, work: DetectionWork) -> Any | None:
        """Run one detector. Returns _FAILED on any failure (never raises)."""
        try:
            if self._settings is None:
                return None
            if self._llm is None:
                self._llm = make_structured_llm(self._settings)
            det = DETECTORS[name]
            user = det.user_template.format(
                history="(none)",
                user_message=work.user_message,
                assistant_reply=work.assistant_reply,
            )
            return await async_structured_call(
                llm=self._llm,
                system=det.system,
                user=user,
                response_model=det.response_model,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "detector failed detector=%s error_type=%s", name, type(exc).__name__
            )
            return _FAILED

    async def _apply(self, name: str, result: Any, work: DetectionWork) -> None:
        now = datetime.now(UTC)
        handler = getattr(self, f"_apply_{name}")
        await handler(result, work, now)

    async def _apply_trust(self, result, work: DetectionWork, now: datetime) -> None:
        for hit in result.signals:
            await self._repo.add_signal(
                user_id=work.user_id,
                kind="trust",
                signal=hit.signal.lower(),
                occurred_at=now,
                expires_at=None,
                counts_toward_stage=True,
                metadata={"confidence": hit.confidence},
            )

    async def _apply_dependency(
        self, result, work: DetectionWork, now: datetime
    ) -> None:
        for hit in result.signals:
            sig = hit.signal.lower()
            ttl = _SHORT_EXPIRY if sig in _SHORT_EXPIRY_SIGNALS else _LONG_EXPIRY
            await self._repo.add_signal(
                user_id=work.user_id,
                kind="dependency",
                signal=sig,
                occurred_at=now,
                expires_at=now + ttl,
                counts_toward_stage=True,
                metadata={"confidence": hit.confidence},
            )
        if result.people_mentioned:
            await self._repo.add_signal(
                user_id=work.user_id,
                kind="people",
                signal="mention",
                occurred_at=now,
                expires_at=None,
                counts_toward_stage=False,
                metadata={"names": list(result.people_mentioned)},
            )

    async def _apply_trait_candidate(
        self, result, work: DetectionWork, now: datetime
    ) -> None:
        existing = await self._repo.list_traits(work.user_id)
        for cand in result.candidates:
            if cand.sensitive or trait_is_sensitive(cand.label, cand.quote):
                continue
            trait = next(
                (t for t in existing if t.kind == cand.kind and t.label == cand.label),
                None,
            )
            status = trait.status if trait else TraitStatus.NOTICED.value
            pos = (trait.positive_count if trait else 0) + 1
            neg = trait.negative_count if trait else 0
            neu = trait.neutral_count if trait else 0
            days = trait.distinct_days if trait else 0
            last = trait.updated_at if trait and trait.updated_at else None
            if trait is None or last is None or last.date() != now.date():
                days += 1
            mutation = observe_trait(
                kind=cand.kind,
                label=cand.label,
                status=status,
                positive_count=pos,
                negative_count=neg,
                neutral_count=neu,
                distinct_days=days,
                reaction="positive",
                sensitive=False,
            )
            await self._repo.upsert_trait(
                user_id=work.user_id,
                kind=cand.kind,
                label=cand.label,
                status=mutation.status.value,
                positive_count=pos,
                negative_count=neg,
                neutral_count=neu,
                distinct_days=days,
                sensitive=False,
            )

    async def _apply_trait_reaction(
        self, result, work: DetectionWork, now: datetime
    ) -> None:
        if not work.trait_used:
            return
        traits = await self._repo.list_traits(work.user_id)
        trait = next((t for t in traits if t.label == work.trait_used), None)
        if trait is None:
            return
        reaction = result.reaction if result.reaction in (
            "positive", "neutral", "negative"
        ) else "neutral"
        pos, neg, neu = trait.positive_count, trait.negative_count, trait.neutral_count
        if reaction == "positive":
            pos += 1
        elif reaction == "negative":
            neg += 1
        else:
            neu += 1
        was_trial = trait.status == TraitStatus.TRIAL.value
        mutation = observe_trait(
            kind=trait.kind,
            label=trait.label,
            status=trait.status,
            positive_count=pos,
            negative_count=neg,
            neutral_count=neu,
            distinct_days=trait.distinct_days,
            reaction=reaction,
            sensitive=trait.sensitive,
        )
        await self._repo.upsert_trait(
            user_id=work.user_id,
            kind=trait.kind,
            label=trait.label,
            status=mutation.status.value,
            positive_count=pos,
            negative_count=neg,
            neutral_count=neu,
            distinct_days=trait.distinct_days,
            sensitive=trait.sensitive,
        )
        await self._repo.record_trait_usage(
            trait_id=trait.id,
            conversation_id=work.conversation_id,
            assistant_message_id=None,
            trial=was_trial or trial_allowed(work.mode),
        )

    async def _apply_leaning(self, result, work: DetectionWork, now: datetime) -> None:
        evidence = [
            ("humor_style", result.humor_style),
            ("curiosity_domain", result.curiosity_topic),
            ("pushback_manner", result.pushback_manner),
        ]
        if not any(v for _, v in evidence):
            return
        existing = await self._repo.list_leanings(work.user_id)
        length = float(len(work.user_message))
        for kind, value in evidence:
            if not value:
                continue
            row = next(
                (l for l in existing if l.kind == kind and l.value == value), None
            )
            status = row.status if row else "noticed"
            pos = (row.positive_count if row else 0) + 1
            neg = row.negative_count if row else 0
            days = row.distinct_days if row else 0
            last = row.updated_at if row and row.updated_at else None
            if row is None or last is None or last.date() != now.date():
                days += 1
            prior = row.baseline_engagement if row else 0.0
            at_or_above = length >= prior
            n = max(pos, 1)
            baseline = prior + (length - prior) / n
            mutation = observe_leaning(
                kind=kind,
                value=value,
                status=status,
                positive_count=pos,
                negative_count=neg,
                distinct_days=days,
                engagement_at_or_above_baseline=at_or_above,
            )
            await self._repo.upsert_leaning(
                user_id=work.user_id,
                kind=kind,
                value=value,
                status=mutation.status.value,
                positive_count=pos,
                negative_count=neg,
                distinct_days=days,
                baseline_engagement=baseline,
            )

    async def _apply_attunement(
        self, result, work: DetectionWork, now: datetime
    ) -> None:
        for field, value in result.model_dump().items():
            if value:
                await self._repo.add_signal(
                    user_id=work.user_id,
                    kind="attunement",
                    signal=field,
                    occurred_at=now,
                    expires_at=None,
                    counts_toward_stage=False,
                    metadata={},
                )
