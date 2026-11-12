"""Periodic stage recompute and attunement review (spec §8, §11, §13).

Never log message content.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent.config import Settings
from agent.persona.constants.dials import (
    DIAL_FLOORS,
    Dials,
    clamp_dials,
    narrow_rejected_combinations,
)
from agent.persona.constants.temperaments import TEMPERAMENTS
from agent.pg.models import UserPersona
from agent.policy.dependency import compute_dependency_level
from agent.policy.stage import compute_stage
from agent.repositories.persona import PersonaRepository

logger = logging.getLogger(__name__)

ATTUNEMENT_CAP = 2  # max points from the seed, per dial and in total
ATTUNEMENT_STEP = 1  # max points per dial per review
_DIAL_NAMES = tuple(f.name for f in fields(Dials))
_ATTUNEMENT_LOOKBACK = timedelta(days=7)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _cap(value: int) -> int:
    return max(-ATTUNEMENT_CAP, min(ATTUNEMENT_CAP, value))


def _humor_lift_allowed(signals: Mapping[str, Any]) -> bool:
    """§8: Banter (or Everyday with two playful signals in the last four turns),
    no distress in the last two turns, and light teasing already landed."""
    if not signals.get("teasing_landed"):
        return False
    if signals.get("distress_last_two"):
        return False
    mode = signals.get("mode")
    playful = int(signals.get("playful_last_four") or 0)
    return mode == "banter" or (mode == "everyday" and playful >= 2)


def compute_attunement(
    *,
    seed_dials: Dials,
    learned_dials: dict,
    explicit_dials: dict,
    signals: Mapping[str, Any],
    now: datetime,
) -> tuple[Dials, dict, list[str]]:
    """Pure attunement review.

    Returns (effective dials, new learned deltas, reason strings).
    """
    reasons: list[str] = []
    deltas: dict[str, int] = {}
    for name in _DIAL_NAMES:
        raw = _as_int((learned_dials or {}).get(name))
        deltas[name] = _cap(raw) if raw is not None else 0
        if raw is not None and deltas[name] != raw:
            reasons.append(f"{name}: learned delta capped at {ATTUNEMENT_CAP} from seed")

    def nudge(name: str, direction: int, why: str) -> None:
        new = _cap(deltas[name] + direction * ATTUNEMENT_STEP)
        if new != deltas[name]:
            deltas[name] = new
            reasons.append(why)

    if signals.get("short_fragments"):
        nudge("formality", -1, "short fragments: formality lowered")
    if signals.get("ignored_question"):
        nudge("initiative", -1, "ignored questions: initiative lowered")
    if signals.get("positive_pushback"):
        nudge("directness", +1, "positive response to pushback: directness raised")
    if signals.get("explicit_shutdown") is True:
        # Explicit rejection or stated hurt only; silence never lands here.
        target = DIAL_FLOORS.directness - seed_dials.directness
        deltas["directness"] = _cap(target)
        reasons.append("explicit shutdown after critique: directness eased toward floor")

    # Total budget: at most ATTUNEMENT_CAP points of drift from the seed overall.
    budget = ATTUNEMENT_CAP
    for name in _DIAL_NAMES:
        mag = abs(deltas[name])
        if mag > budget:
            deltas[name] = (1 if deltas[name] > 0 else -1) * budget
            reasons.append(f"{name}: learned delta trimmed to total cap {ATTUNEMENT_CAP}")
            mag = budget
        budget -= mag

    learned_out = {k: v for k, v in deltas.items() if v}
    values = {n: getattr(seed_dials, n) + deltas[n] for n in _DIAL_NAMES}

    if _humor_lift_allowed(signals):
        lifted = min(values["humor"] + 1, seed_dials.humor + ATTUNEMENT_CAP)
        if lifted != values["humor"]:
            values["humor"] = lifted
            reasons.append("humor lift: banter conditions hold and teasing has landed")

    for name in _DIAL_NAMES:  # explicit settings always win
        explicit = _as_int((explicit_dials or {}).get(name))
        if explicit is not None:
            values[name] = explicit

    effective = clamp_dials(Dials(**values))
    effective, narrowed = narrow_rejected_combinations(effective)
    reasons.extend(narrowed)
    if not reasons:
        reasons.append("no attunement change")
    return effective, learned_out, reasons


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _signal_view(row: Any, tz: ZoneInfo) -> dict[str, Any]:
    """Signal mapping with the local calendar day resolved in the user's zone."""
    metadata = dict(row.metadata_ or {})
    metadata["local_date"] = row.occurred_at.astimezone(tz).date().isoformat()
    return {
        "signal": row.signal,
        "occurred_at": row.occurred_at,
        "counts_toward_stage": row.counts_toward_stage,
        "metadata": metadata,
    }


class RecomputeWorker:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._scheduler: AsyncIOScheduler | None = None

    async def start(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self.recompute_once,
            "interval",
            minutes=self._settings.stage_recompute_interval_minutes,
            id="stage_recompute",
            replace_existing=True,
        )
        self._scheduler.add_job(
            self.review_attunement_once,
            "interval",
            minutes=self._settings.attunement_review_interval_minutes,
            id="attunement_review",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info(
            "recompute worker started stage_min=%d attunement_min=%d",
            self._settings.stage_recompute_interval_minutes,
            self._settings.attunement_review_interval_minutes,
        )

    async def stop(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    async def _user_ids(self) -> list[str]:
        async with self._session_factory() as session:
            result = await session.execute(select(UserPersona.user_id))
            return list(result.scalars().all())

    async def recompute_once(self) -> int:
        """Recompute stage and dependency for every user; returns users processed."""
        processed = 0
        for user_id in await self._user_ids():
            try:
                await self.recompute_user(user_id)
                processed += 1
            except Exception:
                logger.exception("stage recompute failed user=%s", user_id)
        logger.info("stage recompute users=%d", processed)
        return processed

    async def review_attunement_once(self) -> int:
        processed = 0
        for user_id in await self._user_ids():
            try:
                await self.review_attunement(user_id)
                processed += 1
            except Exception:
                logger.exception("attunement review failed user=%s", user_id)
        logger.info("attunement review users=%d", processed)
        return processed

    async def recompute_user(self, user_id: str, *, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        async with self._session_factory() as session:
            repo = PersonaRepository(session)
            persona = await repo.get(user_id)
            if persona is None:
                return
            tz = _zone(persona.timezone)  # day boundaries use the user's zone

            trust = [_signal_view(r, tz) for r in await repo.list_signals(user_id, "trust")]
            dependency = [
                _signal_view(r, tz) for r in await repo.list_signals(user_id, "dependency")
            ]

            level = compute_dependency_level(
                signals=dependency,
                low_baseline=bool(persona.dependency_low_baseline),
                now=now,
            )
            if level != persona.dependency_level:
                persona.dependency_level_since = now
            if level >= 2 and persona.dependency_level < 2:
                persona.stage_frozen_at = now
            if level == 2 and persona.dependency_level != 2:
                persona.dependency_last_level2_at = now
            persona.dependency_level = level

            exchanges = _as_int((persona.counters or {}).get("exchanges")) or 0
            persona.stage = compute_stage(
                signals=trust,
                exchange_count=exchanges,
                dependency_level=level,
                frozen_at=persona.stage_frozen_at,
                now=now,
            )
            await session.commit()

    async def review_attunement(self, user_id: str, *, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        async with self._session_factory() as session:
            repo = PersonaRepository(session)
            persona = await repo.get(user_id)
            if persona is None:
                return
            temperament = TEMPERAMENTS.get(persona.temperament, TEMPERAMENTS["steady"])
            since = persona.last_attunement_review_at or (now - _ATTUNEMENT_LOOKBACK)
            rows = await repo.list_signals(user_id, "attunement", since=since)
            codes = [r.signal for r in rows]
            leanings = await repo.list_leanings(user_id)
            signals: dict[str, Any] = {
                "explicit_shutdown": "explicit_shutdown" in codes,
                "ignored_question": codes.count("ignored_question") >= 2,
                "playful_last_four": codes[-4:].count("playful"),
                "distress_last_two": "distress" in codes[-2:],
                "teasing_landed": any(
                    l.kind == "humor_style" and l.status != "noticed" for l in leanings
                ),
            }
            explicit = (persona.settings or {}).get("dials", {}) or {}
            _, learned, reasons = compute_attunement(
                seed_dials=temperament.default_dials,
                learned_dials=dict(persona.learned_dials or {}),
                explicit_dials=explicit,
                signals=signals,
                now=now,
            )
            persona.learned_dials = learned
            persona.last_attunement_review_at = now
            await session.commit()
            logger.info("attunement reviewed user=%s changes=%d", user_id, len(reasons))
