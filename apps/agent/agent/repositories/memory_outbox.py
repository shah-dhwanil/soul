from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.pg.models import (
    MemoryOutbox,
    MemoryOutboxJobType,
    MemoryOutboxStatus,
)


class MemoryOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self,
        *,
        user_id: str,
        job_type: MemoryOutboxJobType,
        idempotency_key: str,
        thread_id: UUID | None = None,
        priority: int = 0,
    ) -> MemoryOutbox | None:
        dup = await self._session.execute(
            select(MemoryOutbox.id).where(
                MemoryOutbox.idempotency_key == idempotency_key,
                MemoryOutbox.status.in_(
                    [MemoryOutboxStatus.PENDING, MemoryOutboxStatus.PROCESSING]
                ),
            )
        )
        if dup.scalar_one_or_none() is not None:
            return None
        row = MemoryOutbox(
            user_id=user_id,
            job_type=job_type,
            thread_id=thread_id,
            idempotency_key=idempotency_key,
            priority=priority,
            status=MemoryOutboxStatus.PENDING,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def has_pending_user_batch(self, user_id: str) -> bool:
        stmt = select(
            exists().where(
                MemoryOutbox.user_id == user_id,
                MemoryOutbox.job_type == MemoryOutboxJobType.USER_BATCH,
                MemoryOutbox.status.in_(
                    [MemoryOutboxStatus.PENDING, MemoryOutboxStatus.PROCESSING]
                ),
            )
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def claim_one(self) -> MemoryOutbox | None:
        stmt = (
            select(MemoryOutbox)
            .where(MemoryOutbox.status == MemoryOutboxStatus.PENDING)
            .order_by(MemoryOutbox.priority.desc(), MemoryOutbox.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None

        busy = select(
            exists().where(
                and_(
                    MemoryOutbox.user_id == row.user_id,
                    MemoryOutbox.status == MemoryOutboxStatus.PROCESSING,
                    MemoryOutbox.id != row.id,
                )
            )
        )
        busy_result = await self._session.execute(busy)
        if bool(busy_result.scalar()):
            return None

        row.status = MemoryOutboxStatus.PROCESSING
        row.attempts += 1
        await self._session.flush()
        return row

    async def mark_processed(
        self,
        row: MemoryOutbox,
        *,
        episode_uuid: str,
        conversation_to_id: UUID | None,
    ) -> None:
        row.status = MemoryOutboxStatus.PROCESSED
        row.episode_uuid = episode_uuid
        row.conversation_to_id = conversation_to_id
        row.processed_at = datetime.now(UTC)
        row.last_error = None
        await self._session.flush()

    async def mark_deferred(self, row: MemoryOutbox) -> None:
        row.status = MemoryOutboxStatus.DEFERRED
        row.last_error = "below_min_conversations"
        await self._session.flush()

    async def mark_failed(self, row: MemoryOutbox, error: str) -> None:
        row.status = MemoryOutboxStatus.FAILED
        row.last_error = error[:2000]
        await self._session.flush()

    async def requeue_for_retry(self, row: MemoryOutbox, error: str) -> None:
        row.status = MemoryOutboxStatus.PENDING
        row.last_error = error[:2000]
        await self._session.flush()
