import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent.config import Settings
from agent.pg.models import MemoryIngestJobType
from agent.repositories.memory_ingest_job import MemoryIngestJobRepository
from agent.repositories.memory_ingestion_state import MemoryIngestionStateRepository
from agent.services.ingest import IngestService
from agent.services.memory_outbox import MemoryOutboxService

logger = logging.getLogger(__name__)

OUTBOX_BACKOFF_SECONDS = (1, 5, 30, 120, 600)


def batch_meets_ingest_threshold(count: int, min_count: int) -> bool:
    return count >= min_count


def ingest_min_count_for_job(
    settings: Settings,
    job_type: MemoryIngestJobType,
    *,
    priority: int,
) -> int:
    if job_type == MemoryIngestJobType.USER_BATCH and priority >= 1:
        return settings.min_conversations_for_idle_flush
    if job_type == MemoryIngestJobType.IDLE_CHECKPOINT:
        return settings.min_conversations_for_idle_flush
    return settings.min_conversations_for_ingest


class MemoryWorker:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        ingest_service: IngestService,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._ingest = ingest_service
        self._scheduler: AsyncIOScheduler | None = None
        self._poll_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if not self._settings.memory_ingest_enabled:
            logger.info("memory ingest disabled")
            return
        self._running = True
        if self._settings.graphiti_build_indices_on_startup:
            from agent.graphiti.client import create_graphiti

            graphiti = await create_graphiti(build_indices=True)
            await graphiti.close()
        self._poll_task = asyncio.create_task(self._poll_loop())
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self.discover_ingest_jobs,
            "interval",
            minutes=self._settings.idle_discover_interval_minutes,
            id="discover_ingest_jobs",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info(
            "memory worker started poll_s=%.1f discover_min=%d idle_age_min=%d",
            self._settings.outbox_poll_interval_s,
            self._settings.idle_discover_interval_minutes,
            self._settings.idle_ingest_interval_minutes,
        )

    async def stop(self) -> None:
        self._running = False
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        if self._poll_task is not None:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self.drain_once()
            except Exception:
                logger.exception("memory worker poll error")
            await asyncio.sleep(self._settings.outbox_poll_interval_s)

    async def drain_once(self) -> bool:
        if not self._settings.memory_ingest_enabled:
            return False
        async with self._session_factory() as session:
            job_repo = MemoryIngestJobRepository(session)
            row = await job_repo.claim_one()
            if row is None:
                return False
            try:
                await self._process_job(session, row)
                await session.commit()
                return True
            except Exception as exc:
                msg = str(exc)
                if row.attempts >= self._settings.outbox_max_attempts:
                    await job_repo.mark_failed(row, msg)
                else:
                    await job_repo.requeue_for_retry(row, msg)
                    delay = OUTBOX_BACKOFF_SECONDS[
                        min(
                            row.attempts - 1,
                            len(OUTBOX_BACKOFF_SECONDS) - 1,
                        )
                    ]
                    await asyncio.sleep(delay)
                await session.commit()
                logger.exception(
                    "memory ingest failed job=%s user=%s", row.id, row.user_id
                )
                return False

    async def _process_job(self, session: AsyncSession, row) -> bool:
        state_repo = MemoryIngestionStateRepository(session)
        job_repo = MemoryIngestJobRepository(session)
        max_ep = self._settings.max_conversations_per_episode

        if row.job_type in (
            MemoryIngestJobType.THREAD_CLOSED,
            MemoryIngestJobType.IDLE_CHECKPOINT,
        ):
            if row.thread_id is None:
                await job_repo.mark_failed(row, "missing thread_id")
                return True
            min_count = ingest_min_count_for_job(
                self._settings, row.job_type, priority=row.priority
            )
            conversations = await state_repo.list_pending_conversations_for_thread(
                row.thread_id, limit=max_ep
            )
            if not batch_meets_ingest_threshold(len(conversations), min_count):
                await job_repo.mark_deferred(row)
                return True
        elif row.job_type == MemoryIngestJobType.USER_BATCH:
            min_count = ingest_min_count_for_job(
                self._settings, row.job_type, priority=row.priority
            )
            conversations = await state_repo.list_pending_conversations_for_user(
                row.user_id, limit=max_ep
            )
            if not batch_meets_ingest_threshold(len(conversations), min_count):
                await job_repo.mark_deferred(row)
                return True
        else:
            await job_repo.mark_failed(row, f"unknown job_type {row.job_type}")
            return True

        if not conversations:
            await job_repo.mark_processed(
                row, episode_uuid="", conversation_to_id=None
            )
            return True

        episode_uuid = await self._ingest.ingest_conversations(
            session,
            user_id=row.user_id,
            job=row,
            conversations=conversations,
        )
        conversation_to_id = conversations[-1].id
        await job_repo.mark_processed(
            row,
            episode_uuid=episode_uuid,
            conversation_to_id=conversation_to_id,
        )
        if row.job_type == MemoryIngestJobType.USER_BATCH:
            await job_repo.mark_deferred_superseded_for_user(
                row.user_id,
                conversation_to_id=conversation_to_id,
            )
        return True

    async def discover_ingest_jobs(self) -> None:
        if not self._settings.memory_ingest_enabled:
            return
        min_ingest = self._settings.min_conversations_for_ingest
        idle_age = self._settings.idle_ingest_interval_minutes
        user_batch_enqueued = 0
        idle_checkpoint_enqueued = 0
        users_at_min: list[str] = []
        users_deferred: list[str] = []
        stale_threads: list[tuple] = []
        async with self._session_factory() as session:
            state_repo = MemoryIngestionStateRepository(session)
            outbox = MemoryOutboxService(session)
            job_repo = MemoryIngestJobRepository(session)
            users_at_min = await state_repo.list_user_ids_with_min_pending(
                min_count=min_ingest
            )
            users_deferred = await job_repo.list_user_ids_with_deferred_jobs()
            stale_threads = await state_repo.list_threads_with_stale_pending(
                idle_minutes=idle_age
            )
            scheduled_users: set[str] = set()
            for user_id in users_at_min:
                if await outbox.enqueue_user_batch(user_id, priority=0):
                    user_batch_enqueued += 1
                scheduled_users.add(user_id)
            for thread_id, user_id in stale_threads:
                if await outbox.enqueue_idle_checkpoint(user_id, thread_id):
                    idle_checkpoint_enqueued += 1
                scheduled_users.add(user_id)
            for user_id in users_deferred:
                if user_id in scheduled_users:
                    continue
                count = await state_repo.count_pending_for_user(user_id)
                if count == 0:
                    continue
                priority = 0 if count >= min_ingest else 1
                if await outbox.enqueue_user_batch(user_id, priority=priority):
                    user_batch_enqueued += 1
            await session.commit()
        logger.info(
            "discover_ingest_jobs at_min=%d deferred=%d stale_threads=%d "
            "user_batch_enqueued=%d idle_checkpoint_enqueued=%d",
            len(users_at_min),
            len(users_deferred),
            len(stale_threads),
            user_batch_enqueued,
            idle_checkpoint_enqueued,
        )
        await self.drain_once()
