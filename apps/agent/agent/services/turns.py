import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent.config import Settings
from agent.graph.build import build_turn_graph
from agent.graph.deps import GraphDeps
from agent.graph.state import initial_state
from agent.history import ChatTurn, PriorTurn
from agent.model.decision import DecisionModel
from agent.model.query import QueryLLM
from agent.repositories.conversation import ConversationRepository
from agent.repositories.persona import DetectionJobRepository, PersonaRepository
from agent.services.memory import MemoryService
from agent.services.memory_outbox import MemoryOutboxService
from agent.services.threads import ThreadService


@dataclass
class ChatResult:
    thread_id: UUID
    turn_id: UUID
    reply: str
    new_thread: bool
    decisions: dict[str, Any]
    memory_degraded: bool
    conversation_id: UUID | None
    mode: str | None = None
    concern_tier: str | None = None


class TurnService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        checkpointer: BaseCheckpointSaver,
        decision_model: DecisionModel,
        query_llm: QueryLLM,
        memory_service: MemoryService,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._graph = build_turn_graph(checkpointer=checkpointer)
        self._decision_model = decision_model
        self._query_llm = query_llm
        self._memory_service = memory_service

    async def seed_history(
        self, user_id: str, prior: tuple[PriorTurn, ...]
    ) -> None:
        """Insert canned turns for evals without invoking the graph."""
        if not prior:
            return
        async with self._session_factory() as session:
            thread_service = ThreadService(session)
            thread = await thread_service.get_or_create_active(user_id)
            conv_repo = ConversationRepository(session)
            for p in prior:
                await conv_repo.create(
                    thread_id=thread.id,
                    user_message=p.user_message,
                    agent_response=p.agent_response,
                    final_state={"seeded_for_eval": True},
                )
            thread.last_message_at = datetime.now(UTC)
            await session.commit()

    async def handle_turn(self, user_id: str, message: str) -> ChatResult:
        turn_id = uuid4()
        async with self._session_factory() as session:
            thread_service = ThreadService(session)
            thread = await thread_service.get_or_create_active(user_id)
            await PersonaRepository(session).get_or_create(
                user_id,
                locale=self._settings.default_locale,
                timezone=self._settings.default_timezone,
            )
            conv_repo = ConversationRepository(session)
            recent = await conv_repo.list_recent_for_thread(
                thread.id, self._settings.decision_history_limit
            )
            decision_history = [ChatTurn.from_conversation(r) for r in recent]

            state = initial_state(
                user_id=user_id,
                turn_id=turn_id,
                db_thread_id=thread.id,
                user_message=message,
                decision_history=decision_history,
            )
            deps = GraphDeps(
                session=session,
                settings=self._settings,
                decision_model=self._decision_model,
                query_llm=self._query_llm,
                memory_service=self._memory_service,
            )
            config = {
                "configurable": {
                    "thread_id": str(turn_id),
                    "deps": deps,
                }
            }
            logger.info(
                "handle_turn start user=%s turn=%s message_len=%d",
                user_id,
                turn_id,
                len(message),
            )
            result = await self._graph.ainvoke(state, config)
            logger.info(
                "handle_turn done turn=%s memory_degraded=%s reply_len=%d",
                turn_id,
                result.get("memory_degraded"),
                len(result.get("reply") or ""),
            )
            db_thread_id = UUID(result["db_thread_id"])
            conv = await conv_repo.create(
                thread_id=db_thread_id,
                user_message=message,
                agent_response=result.get("reply", ""),
                final_state=result.get("final_state") or {},
            )
            conv.finished_at = datetime.now(UTC)
            persisted = (result.get("final_state") or {}).get("persona") or {}
            conv.mode = persisted.get("mode")
            conv.concern_tier = persisted.get("concern_tier")
            conv.dependency_level = persisted.get("dependency_level")
            conv.stage = persisted.get("stage")
            conv.asked_question = bool(persisted.get("asked_question"))
            conv.trait_used = persisted.get("trait_used")
            conv.validation = persisted.get("validation") or {}
            conv.persona_version = persisted.get("persona_version")
            await DetectionJobRepository(session).enqueue(
                user_id=user_id, conversation_id=conv.id
            )
            from agent.repositories.thread import ThreadRepository

            thread_row = await ThreadRepository(session).get(db_thread_id)
            if thread_row is not None:
                thread_row.last_message_at = datetime.now(UTC)

            if self._settings.memory_ingest_enabled:
                outbox_svc = MemoryOutboxService(session)
                await outbox_svc.enqueue_conversation_turn(
                    conversation_id=conv.id,
                    user_id=user_id,
                    thread_id=db_thread_id,
                )
                ingest_pending = (result.get("final_state") or {}).get(
                    "ingest_pending"
                )
                if ingest_pending:
                    await outbox_svc.enqueue_thread_closed(
                        user_id,
                        UUID(str(ingest_pending)),
                    )

            await session.commit()

            return ChatResult(
                thread_id=db_thread_id,
                turn_id=turn_id,
                reply=result.get("reply", ""),
                new_thread=bool(result.get("new_thread_created")),
                decisions=result.get("decisions") or {},
                memory_degraded=bool(result.get("memory_degraded")),
                conversation_id=conv.id,
                mode=conv.mode,
                concern_tier=conv.concern_tier,
            )
