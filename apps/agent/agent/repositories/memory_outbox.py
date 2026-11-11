from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.pg.models import MemoryOutbox


class MemoryOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue_conversation(
        self,
        *,
        conversation_id: UUID,
        user_id: str,
        thread_id: UUID,
    ) -> MemoryOutbox | None:
        dup = await self._session.execute(
            select(MemoryOutbox.id).where(
                MemoryOutbox.conversation_id == conversation_id
            )
        )
        if dup.scalar_one_or_none() is not None:
            return None
        row = MemoryOutbox(
            conversation_id=conversation_id,
            user_id=user_id,
            thread_id=thread_id,
        )
        self._session.add(row)
        await self._session.flush()
        return row
