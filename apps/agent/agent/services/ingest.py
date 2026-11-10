import logging

from sqlalchemy.ext.asyncio import AsyncSession

from agent.config import Settings
from agent.graphiti.ingest import add_episode_for_batch
from agent.pg.models import Conversation, MemoryOutbox
from agent.repositories.thread import ThreadRepository

logger = logging.getLogger(__name__)


class IngestService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def ingest_conversations(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        outbox: MemoryOutbox,
        conversations: list[Conversation],
    ) -> str:
        key = f"{outbox.job_type.value}:{outbox.id}"
        episode_uuid = await add_episode_for_batch(
            user_id=user_id,
            idempotency_key=key,
            conversations=conversations,
        )
        thread_repo = ThreadRepository(session)
        last_by_thread: dict[UUID, UUID] = {}
        for conv in conversations:
            last_by_thread[conv.thread_id] = conv.id
        for thread_id, conv_id in last_by_thread.items():
            await thread_repo.set_ingested_through(thread_id, conv_id)
        logger.info(
            "ingested user=%s episode=%s conversations=%d threads=%d",
            user_id,
            episode_uuid,
            len(conversations),
            len(last_by_thread),
        )
        return episode_uuid
