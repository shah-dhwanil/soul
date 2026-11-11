import logging

from sqlalchemy.ext.asyncio import AsyncSession

from agent.config import Settings
from agent.graphiti.ingest import add_episode_for_batch
from agent.pg.models import Conversation, MemoryIngestJob
from agent.repositories.memory_ingestion_state import MemoryIngestionStateRepository

logger = logging.getLogger(__name__)


class IngestService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def ingest_conversations(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        job: MemoryIngestJob,
        conversations: list[Conversation],
    ) -> str:
        key = f"{job.job_type.value}:{job.id}"
        episode_uuid = await add_episode_for_batch(
            user_id=user_id,
            idempotency_key=key,
            conversations=conversations,
        )
        conv_ids = [c.id for c in conversations]
        await MemoryIngestionStateRepository(session).mark_ingested(
            conv_ids, episode_uuid=episode_uuid
        )
        threads = {c.thread_id for c in conversations}
        logger.info(
            "ingested user=%s episode=%s conversations=%d threads=%d",
            user_id,
            episode_uuid,
            len(conversations),
            len(threads),
        )
        return episode_uuid
