from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agent.pg.models import Thread
from agent.repositories.thread import ThreadRepository


class ThreadService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ThreadRepository(session)

    async def get_or_create_active(self, user_id: str) -> Thread:
        thread = await self._repo.get_active_for_user(user_id)
        if thread is not None:
            return thread
        return await self._repo.create_active(user_id)

    async def complete(self, thread_id: UUID) -> None:
        await self._repo.complete(thread_id)

    async def rotate(self, user_id: str, old_thread_id: UUID) -> UUID:
        await self._repo.complete(old_thread_id)
        new_thread = await self._repo.create_active(user_id)
        return new_thread.id
