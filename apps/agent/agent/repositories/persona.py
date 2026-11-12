"""Persona state and detection job repositories. Never log message content."""

from datetime import UTC, datetime
from dataclasses import asdict
from uuid import UUID

from sqlalchemy import and_, delete, exists, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from agent.persona.constants.temperaments import TEMPERAMENTS
from agent.pg.models import (
    DetectionJob,
    UserLeaning,
    UserPersona,
    UserSignal,
    UserTrait,
)


class PersonaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: str) -> UserPersona | None:
        result = await self._session.execute(
            select(UserPersona).where(UserPersona.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        user_id: str,
        *,
        temperament: str = "steady",
        locale: str = "en-US",
        timezone: str = "UTC",
    ) -> UserPersona:
        # Race-safe: concurrent first turns both INSERT; the loser does nothing.
        await self._session.execute(
            pg_insert(UserPersona)
            .values(
                user_id=user_id,
                temperament=temperament,
                locale=locale,
                timezone=timezone,
                dials={},
                learned_dials={},
                stage=1,
                dependency_level=0,
                dependency_low_baseline=False,
                settings={},
                counters={},
            )
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        result = await self._session.execute(
            select(UserPersona)
            .where(UserPersona.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one()

    async def upsert_dials(self, user_id: str, dials: dict, learned: dict) -> None:
        persona = await self.get_or_create(user_id)
        persona.dials = dials
        persona.learned_dials = learned
        await self._session.flush()

    async def add_signal(
        self,
        *,
        user_id: str,
        kind: str,
        signal: str,
        occurred_at: datetime,
        expires_at: datetime | None,
        counts_toward_stage: bool,
        metadata: dict,
    ) -> UserSignal:
        row = UserSignal(
            user_id=user_id,
            kind=kind,
            signal=signal,
            occurred_at=occurred_at,
            expires_at=expires_at,
            counts_toward_stage=counts_toward_stage,
            metadata_=metadata,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_signals(
        self, user_id: str, kind: str, *, since: datetime | None = None
    ) -> list[UserSignal]:
        stmt = select(UserSignal).where(
            UserSignal.user_id == user_id, UserSignal.kind == kind
        )
        if since is not None:
            stmt = stmt.where(UserSignal.occurred_at >= since)
        stmt = stmt.order_by(UserSignal.occurred_at.asc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_traits(
        self, user_id: str, *, status: str | None = None
    ) -> list[UserTrait]:
        stmt = select(UserTrait).where(UserTrait.user_id == user_id)
        if status is not None:
            stmt = stmt.where(UserTrait.status == status)
        result = await self._session.execute(stmt.order_by(UserTrait.created_at))
        return list(result.scalars().all())

    async def upsert_trait(
        self,
        *,
        user_id: str,
        kind: str,
        label: str,
        status: str,
        positive_count: int,
        negative_count: int,
        neutral_count: int,
        distinct_days: int,
        sensitive: bool,
    ) -> UserTrait:
        result = await self._session.execute(
            select(UserTrait).where(
                UserTrait.user_id == user_id,
                UserTrait.kind == kind,
                UserTrait.label == label,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = UserTrait(user_id=user_id, kind=kind, label=label)
            self._session.add(row)
        row.status = status
        row.positive_count = positive_count
        row.negative_count = negative_count
        row.neutral_count = neutral_count
        row.distinct_days = distinct_days
        row.sensitive = sensitive
        await self._session.flush()
        return row

    async def record_trait_usage(
        self,
        *,
        trait_id: UUID,
        conversation_id: UUID,
        assistant_message_id: UUID | None,
        trial: bool,
    ) -> None:
        # conversation_id / assistant_message_id / trial are accepted for the
        # interface; the trait row only tracks recency of use.
        await self._session.execute(
            update(UserTrait)
            .where(UserTrait.id == trait_id)
            .values(last_used_at=datetime.now(UTC))
        )
        await self._session.flush()

    async def list_leanings(
        self, user_id: str, *, status: str | None = None
    ) -> list[UserLeaning]:
        stmt = select(UserLeaning).where(UserLeaning.user_id == user_id)
        if status is not None:
            stmt = stmt.where(UserLeaning.status == status)
        result = await self._session.execute(stmt.order_by(UserLeaning.created_at))
        return list(result.scalars().all())

    async def upsert_leaning(
        self,
        *,
        user_id: str,
        kind: str,
        value: str,
        status: str,
        positive_count: int,
        negative_count: int,
        distinct_days: int,
        baseline_engagement: float,
    ) -> UserLeaning:
        result = await self._session.execute(
            select(UserLeaning).where(
                UserLeaning.user_id == user_id,
                UserLeaning.kind == kind,
                UserLeaning.value == value,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = UserLeaning(user_id=user_id, kind=kind, value=value)
            self._session.add(row)
        if row.status != status and status == "tilt" and row.tilt_started_at is None:
            row.tilt_started_at = datetime.now(UTC)
        row.status = status
        row.positive_count = positive_count
        row.negative_count = negative_count
        row.distinct_days = distinct_days
        row.baseline_engagement = baseline_engagement
        await self._session.flush()
        return row

    async def set_settings(self, user_id: str, settings: dict) -> None:
        persona = await self.get_or_create(user_id)
        persona.settings = settings
        await self._session.flush()

    async def reseed(self, user_id: str, temperament: str) -> dict:
        """Re-seed the persona with a temperament and its default dials.

        The explicit dial overrides are dropped, so the dials are the new
        temperament's defaults. Learned dials are left alone, because they
        were learned rather than chosen.
        """
        persona = await self.get_or_create(user_id)
        seed = asdict(TEMPERAMENTS[temperament].default_dials)
        settings = dict(persona.settings or {})
        settings.pop("dials", None)
        persona.temperament = temperament
        persona.dials = dict(seed)
        persona.settings = settings
        await self._session.flush()
        return {
            "user_id": persona.user_id,
            "temperament": persona.temperament,
            "dials": persona.dials,
            "learned_dials": persona.learned_dials,
            "settings": persona.settings,
        }

    async def reset_learned(self, user_id: str) -> None:
        persona = await self.get_or_create(user_id)
        persona.learned_dials = {}
        await self._session.flush()

    async def rename_trait(
        self, user_id: str, trait_id: UUID, label: str
    ) -> UserTrait | None:
        result = await self._session.execute(
            select(UserTrait).where(
                UserTrait.id == trait_id, UserTrait.user_id == user_id
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.label = label
        await self._session.flush()
        return row

    async def delete_trait(self, user_id: str, trait_id: UUID) -> bool:
        result = await self._session.execute(
            delete(UserTrait).where(
                UserTrait.id == trait_id, UserTrait.user_id == user_id
            )
        )
        await self._session.flush()
        return bool(result.rowcount)

    async def delete_all(self, user_id: str) -> None:
        for model in (UserSignal, UserTrait, UserLeaning, DetectionJob, UserPersona):
            await self._session.execute(
                delete(model).where(model.user_id == user_id)
            )
        await self._session.flush()


class DetectionJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, *, user_id: str, conversation_id: UUID) -> None:
        # The partial unique index keeps one active job per conversation.
        await self._session.execute(
            pg_insert(DetectionJob)
            .values(
                user_id=user_id,
                conversation_id=conversation_id,
                status="pending",
                attempts=0,
            )
            .on_conflict_do_nothing(
                index_elements=["conversation_id"],
                index_where=text("status IN ('pending','processing')"),
            )
        )
        await self._session.flush()

    async def claim_one(self) -> DetectionJob | None:
        stmt = (
            select(DetectionJob)
            .where(DetectionJob.status == "pending")
            .order_by(DetectionJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None

        busy = select(
            exists().where(
                and_(
                    DetectionJob.user_id == row.user_id,
                    DetectionJob.status == "processing",
                    DetectionJob.id != row.id,
                )
            )
        )
        if bool((await self._session.execute(busy)).scalar()):
            return None

        row.status = "processing"
        row.attempts += 1
        await self._session.flush()
        return row

    async def mark_processed(self, row: DetectionJob) -> None:
        row.status = "processed"
        row.processed_at = datetime.now(UTC)
        row.last_error = None
        await self._session.flush()

    async def mark_failed(self, row: DetectionJob, error: str) -> None:
        row.status = "failed"
        row.last_error = error[:2000]
        await self._session.flush()

    async def requeue_for_retry(self, row: DetectionJob, error: str) -> None:
        row.status = "pending"
        row.last_error = error[:2000]
        await self._session.flush()
