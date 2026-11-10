from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.pg.models import Conversation, Thread


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

    def _uningested_condition(self):
        watermark = Conversation.__table__.alias("ingest_wm")
        return or_(
            Thread.ingested_through_conversation_id.is_(None),
            Conversation.started_at
            > select(watermark.c.started_at)
            .where(watermark.c.id == Thread.ingested_through_conversation_id)
            .scalar_subquery(),
        )

    async def count_uningested_for_thread(self, thread_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Conversation)
            .join(Thread, Conversation.thread_id == Thread.id)
            .where(Conversation.thread_id == thread_id)
            .where(self._uningested_condition())
        )
        result = await self._session.execute(stmt)
        return int(result.scalar() or 0)

    async def list_uningested_for_thread(
        self, thread_id: UUID, *, limit: int | None = None
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .join(Thread, Conversation.thread_id == Thread.id)
            .where(Conversation.thread_id == thread_id)
            .where(self._uningested_condition())
            .order_by(Conversation.started_at.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_uningested_for_user(self, user_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(Conversation)
            .join(Thread, Conversation.thread_id == Thread.id)
            .where(Thread.user_id == user_id)
            .where(self._uningested_condition())
        )
        result = await self._session.execute(stmt)
        return int(result.scalar() or 0)

    async def list_uningested_for_user(
        self, user_id: str, *, limit: int
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .join(Thread, Conversation.thread_id == Thread.id)
            .where(Thread.user_id == user_id)
            .where(self._uningested_condition())
            .order_by(Conversation.started_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_users_with_min_uningested(self, *, min_count: int) -> list[str]:
        stmt = (
            select(Thread.user_id)
            .join(Conversation, Conversation.thread_id == Thread.id)
            .where(self._uningested_condition())
            .group_by(Thread.user_id)
            .having(func.count(Conversation.id) >= min_count)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
