from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.pg.models import Conversation


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_thread(
        self,
        thread_id: UUID,
        *,
        limit: int | None = None,
        newest_first: bool = False,
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.thread_id == thread_id)
            .order_by(
                Conversation.started_at.desc()
                if newest_first
                else Conversation.started_at.asc()
            )
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        if newest_first:
            rows.reverse()
        return rows

    async def list_recent_for_thread(
        self, thread_id: UUID, limit: int
    ) -> list[Conversation]:
        return await self.list_by_thread(thread_id, limit=limit)

    async def create(
        self,
        *,
        thread_id: UUID,
        user_message: str,
        agent_response: str,
        final_state: dict,
    ) -> Conversation:
        row = Conversation(
            thread_id=thread_id,
            user_message=user_message,
            agent_response=agent_response,
            final_state=final_state,
        )
        self._session.add(row)
        await self._session.flush()
        return row
