from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.pg.models import (
    Conversation,
    MemoryIngestionState,
    MemoryIngestionStateStatus,
)


class MemoryIngestionStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue_pending(
        self,
        *,
        conversation_id: UUID,
        user_id: str,
        thread_id: UUID,
    ) -> MemoryIngestionState:
        existing = await self._session.get(MemoryIngestionState, conversation_id)
        if existing is not None:
            return existing
        row = MemoryIngestionState(
            conversation_id=conversation_id,
            user_id=user_id,
            thread_id=thread_id,
            status=MemoryIngestionStateStatus.PENDING,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def mark_ingested(
        self,
        conversation_ids: list[UUID],
        *,
        episode_uuid: str,
    ) -> None:
        if not conversation_ids:
            return
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(MemoryIngestionState).where(
                MemoryIngestionState.conversation_id.in_(conversation_ids)
            )
        )
        for row in result.scalars().all():
            row.status = MemoryIngestionStateStatus.INGESTED
            row.episode_uuid = episode_uuid
            row.ingested_at = now
            row.last_error = None
        await self._session.flush()

    async def list_pending_conversations_for_thread(
        self, thread_id: UUID, *, limit: int | None = None
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .join(
                MemoryIngestionState,
                MemoryIngestionState.conversation_id == Conversation.id,
            )
            .where(
                MemoryIngestionState.thread_id == thread_id,
                MemoryIngestionState.status == MemoryIngestionStateStatus.PENDING,
            )
            .order_by(Conversation.started_at.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_pending_conversations_for_user(
        self, user_id: str, *, limit: int
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .join(
                MemoryIngestionState,
                MemoryIngestionState.conversation_id == Conversation.id,
            )
            .where(
                MemoryIngestionState.user_id == user_id,
                MemoryIngestionState.status == MemoryIngestionStateStatus.PENDING,
            )
            .order_by(Conversation.started_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_pending_for_user(self, user_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(MemoryIngestionState)
            .where(
                MemoryIngestionState.user_id == user_id,
                MemoryIngestionState.status == MemoryIngestionStateStatus.PENDING,
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar() or 0)

    async def list_user_ids_with_min_pending(self, *, min_count: int) -> list[str]:
        stmt = (
            select(MemoryIngestionState.user_id)
            .where(MemoryIngestionState.status == MemoryIngestionStateStatus.PENDING)
            .group_by(MemoryIngestionState.user_id)
            .having(func.count(MemoryIngestionState.conversation_id) >= min_count)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_threads_with_stale_pending(
        self, *, idle_minutes: int
    ) -> list[tuple[UUID, str]]:
        cutoff = datetime.now(UTC) - timedelta(minutes=idle_minutes)
        stmt = (
            select(MemoryIngestionState.thread_id, MemoryIngestionState.user_id)
            .join(
                Conversation,
                Conversation.id == MemoryIngestionState.conversation_id,
            )
            .where(
                MemoryIngestionState.status == MemoryIngestionStateStatus.PENDING,
                Conversation.finished_at <= cutoff,
            )
            .group_by(MemoryIngestionState.thread_id, MemoryIngestionState.user_id)
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
