from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agent.pg.models import MemoryIngestJobType
from agent.repositories.memory_ingest_job import MemoryIngestJobRepository
from agent.repositories.memory_ingestion_state import MemoryIngestionStateRepository
from agent.repositories.memory_outbox import MemoryOutboxRepository


class MemoryOutboxService:
    def __init__(self, session: AsyncSession) -> None:
        self._outbox = MemoryOutboxRepository(session)
        self._state = MemoryIngestionStateRepository(session)
        self._jobs = MemoryIngestJobRepository(session)

    async def enqueue_conversation_turn(
        self,
        *,
        conversation_id: UUID,
        user_id: str,
        thread_id: UUID,
    ) -> None:
        await self._outbox.enqueue_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            thread_id=thread_id,
        )
        await self._state.enqueue_pending(
            conversation_id=conversation_id,
            user_id=user_id,
            thread_id=thread_id,
        )

    async def enqueue_thread_closed(self, user_id: str, thread_id: UUID) -> None:
        await self._jobs.enqueue(
            user_id=user_id,
            job_type=MemoryIngestJobType.THREAD_CLOSED,
            thread_id=thread_id,
            idempotency_key=f"thread_closed:{thread_id}",
        )

    async def enqueue_user_batch(self, user_id: str, *, priority: int = 0) -> bool:
        if await self._jobs.has_pending_user_batch(user_id):
            return False
        if await self._jobs.requeue_deferred_user_batch(user_id, priority=priority):
            return True
        row = await self._jobs.enqueue(
            user_id=user_id,
            job_type=MemoryIngestJobType.USER_BATCH,
            thread_id=None,
            idempotency_key=f"user_batch:{user_id}",
            priority=priority,
        )
        return row is not None

    async def enqueue_idle_checkpoint(
        self, user_id: str, thread_id: UUID, *, priority: int = 1
    ) -> bool:
        if await self._jobs.has_pending_idle_checkpoint(thread_id):
            return False
        if await self._jobs.requeue_deferred_idle_checkpoint(
            thread_id, priority=priority
        ):
            return True
        row = await self._jobs.enqueue(
            user_id=user_id,
            job_type=MemoryIngestJobType.IDLE_CHECKPOINT,
            thread_id=thread_id,
            idempotency_key=f"idle_checkpoint:{thread_id}",
            priority=priority,
        )
        return row is not None
