from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent.pg.models import (
    MemoryIngestJob,
    MemoryIngestJobStatus,
    MemoryIngestJobType,
)


class MemoryIngestJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self,
        *,
        user_id: str,
        job_type: MemoryIngestJobType,
        idempotency_key: str,
        thread_id: UUID | None = None,
        priority: int = 0,
    ) -> MemoryIngestJob | None:
        dup = await self._session.execute(
            select(MemoryIngestJob.id).where(
                MemoryIngestJob.idempotency_key == idempotency_key,
                MemoryIngestJob.status.in_(
                    [
                        MemoryIngestJobStatus.PENDING,
                        MemoryIngestJobStatus.PROCESSING,
                    ]
                ),
            )
        )
        if dup.scalar_one_or_none() is not None:
            return None
        row = MemoryIngestJob(
            user_id=user_id,
            job_type=job_type,
            thread_id=thread_id,
            idempotency_key=idempotency_key,
            priority=priority,
            status=MemoryIngestJobStatus.PENDING,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def has_pending_user_batch(self, user_id: str) -> bool:
        stmt = select(
            exists().where(
                MemoryIngestJob.user_id == user_id,
                MemoryIngestJob.job_type == MemoryIngestJobType.USER_BATCH,
                MemoryIngestJob.status.in_(
                    [
                        MemoryIngestJobStatus.PENDING,
                        MemoryIngestJobStatus.PROCESSING,
                    ]
                ),
            )
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def has_pending_idle_checkpoint(self, thread_id: UUID) -> bool:
        stmt = select(
            exists().where(
                MemoryIngestJob.thread_id == thread_id,
                MemoryIngestJob.job_type == MemoryIngestJobType.IDLE_CHECKPOINT,
                MemoryIngestJob.status.in_(
                    [
                        MemoryIngestJobStatus.PENDING,
                        MemoryIngestJobStatus.PROCESSING,
                    ]
                ),
            )
        )
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def claim_one(self) -> MemoryIngestJob | None:
        stmt = (
            select(MemoryIngestJob)
            .where(MemoryIngestJob.status == MemoryIngestJobStatus.PENDING)
            .order_by(
                MemoryIngestJob.priority.desc(),
                MemoryIngestJob.created_at.asc(),
            )
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
                    MemoryIngestJob.user_id == row.user_id,
                    MemoryIngestJob.status == MemoryIngestJobStatus.PROCESSING,
                    MemoryIngestJob.id != row.id,
                )
            )
        )
        busy_result = await self._session.execute(busy)
        if bool(busy_result.scalar()):
            return None

        row.status = MemoryIngestJobStatus.PROCESSING
        row.attempts += 1
        await self._session.flush()
        return row

    async def mark_processed(
        self,
        row: MemoryIngestJob,
        *,
        episode_uuid: str,
        conversation_to_id: UUID | None,
    ) -> None:
        row.status = MemoryIngestJobStatus.PROCESSED
        row.episode_uuid = episode_uuid
        row.conversation_to_id = conversation_to_id
        row.processed_at = datetime.now(UTC)
        row.last_error = None
        await self._session.flush()

    async def mark_deferred(self, row: MemoryIngestJob) -> None:
        row.status = MemoryIngestJobStatus.DEFERRED
        row.last_error = "below_min_conversations"
        await self._session.flush()

    async def mark_failed(self, row: MemoryIngestJob, error: str) -> None:
        row.status = MemoryIngestJobStatus.FAILED
        row.last_error = error[:2000]
        await self._session.flush()

    async def requeue_for_retry(self, row: MemoryIngestJob, error: str) -> None:
        row.status = MemoryIngestJobStatus.PENDING
        row.last_error = error[:2000]
        await self._session.flush()

    async def list_user_ids_with_deferred_jobs(self) -> list[str]:
        stmt = (
            select(MemoryIngestJob.user_id)
            .where(MemoryIngestJob.status == MemoryIngestJobStatus.DEFERRED)
            .distinct()
            .order_by(MemoryIngestJob.user_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def requeue_deferred_user_batch(
        self, user_id: str, *, priority: int = 1
    ) -> bool:
        stmt = (
            select(MemoryIngestJob)
            .where(
                MemoryIngestJob.user_id == user_id,
                MemoryIngestJob.job_type == MemoryIngestJobType.USER_BATCH,
                MemoryIngestJob.status == MemoryIngestJobStatus.DEFERRED,
            )
            .limit(1)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return False
        row.status = MemoryIngestJobStatus.PENDING
        row.priority = priority
        row.last_error = None
        await self._session.flush()
        return True

    async def requeue_deferred_idle_checkpoint(
        self, thread_id: UUID, *, priority: int = 1
    ) -> bool:
        stmt = (
            select(MemoryIngestJob)
            .where(
                MemoryIngestJob.thread_id == thread_id,
                MemoryIngestJob.job_type == MemoryIngestJobType.IDLE_CHECKPOINT,
                MemoryIngestJob.status == MemoryIngestJobStatus.DEFERRED,
            )
            .limit(1)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return False
        row.status = MemoryIngestJobStatus.PENDING
        row.priority = priority
        row.last_error = None
        await self._session.flush()
        return True

    async def mark_deferred_superseded_for_user(
        self,
        user_id: str,
        *,
        conversation_to_id: UUID | None,
    ) -> int:
        now = datetime.now(UTC)
        stmt = (
            update(MemoryIngestJob)
            .where(
                MemoryIngestJob.user_id == user_id,
                MemoryIngestJob.status == MemoryIngestJobStatus.DEFERRED,
                MemoryIngestJob.job_type.in_(
                    [
                        MemoryIngestJobType.THREAD_CLOSED,
                        MemoryIngestJobType.IDLE_CHECKPOINT,
                    ]
                ),
            )
            .values(
                status=MemoryIngestJobStatus.PROCESSED,
                episode_uuid="",
                conversation_to_id=conversation_to_id,
                processed_at=now,
                last_error="superseded_by_user_batch",
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount or 0)
