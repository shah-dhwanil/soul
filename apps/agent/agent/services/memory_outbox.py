from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agent.pg.models import MemoryOutboxJobType
from agent.repositories.memory_outbox import MemoryOutboxRepository


class MemoryOutboxService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = MemoryOutboxRepository(session)

    async def enqueue_thread_closed(self, user_id: str, thread_id: UUID) -> None:
        await self._repo.enqueue(
            user_id=user_id,
            job_type=MemoryOutboxJobType.THREAD_CLOSED,
            thread_id=thread_id,
            idempotency_key=f"thread_closed:{thread_id}",
        )

    async def enqueue_user_batch(self, user_id: str, *, priority: int = 0) -> bool:
        if await self._repo.has_pending_user_batch(user_id):
            return False
        if await self._repo.requeue_deferred_user_batch(user_id, priority=priority):
            return True
        row = await self._repo.enqueue(
            user_id=user_id,
            job_type=MemoryOutboxJobType.USER_BATCH,
            thread_id=None,
            idempotency_key=f"user_batch:{user_id}",
            priority=priority,
        )
        return row is not None
