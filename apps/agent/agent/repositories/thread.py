from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.pg.models import Thread, ThreadStatus


class ThreadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_for_user(self, user_id: str) -> Thread | None:
        result = await self._session.execute(
            select(Thread).where(
                Thread.user_id == user_id,
                Thread.status == ThreadStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def create_active(self, user_id: str) -> Thread:
        thread = Thread(user_id=user_id, status=ThreadStatus.ACTIVE)
        self._session.add(thread)
        await self._session.flush()
        return thread

    async def complete(self, thread_id: UUID) -> None:
        result = await self._session.execute(
            select(Thread).where(Thread.id == thread_id)
        )
        thread = result.scalar_one()
        thread.status = ThreadStatus.COMPLETED
        await self._session.flush()

    async def get(self, thread_id: UUID) -> Thread | None:
        result = await self._session.execute(
            select(Thread).where(Thread.id == thread_id)
        )
        return result.scalar_one_or_none()

    async def set_ingested_through(
        self, thread_id: UUID, conversation_id: UUID
    ) -> None:
        result = await self._session.execute(
            select(Thread).where(Thread.id == thread_id)
        )
        thread = result.scalar_one_or_none()
        if thread is not None:
            thread.ingested_through_conversation_id = conversation_id
            await self._session.flush()
