from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent.config import Settings
from agent.graph.build import build_turn_graph
from agent.graph.deps import GraphDeps
from agent.graph.state import initial_state
from agent.history import ChatTurn
from agent.model.decision import DecisionModel
from agent.model.query import QueryLLM
from agent.repositories.conversation import ConversationRepository
from agent.services.memory import MemoryService
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

    async def handle_turn(self, user_id: str, message: str) -> ChatResult:
        turn_id = uuid4()
        async with self._session_factory() as session:
            thread_service = ThreadService(session)
            thread = await thread_service.get_or_create_active(user_id)
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
            result = await self._graph.ainvoke(state, config)
            db_thread_id = UUID(result["db_thread_id"])
            conv = await conv_repo.create(
                thread_id=db_thread_id,
                user_message=message,
                agent_response=result.get("reply", ""),
                final_state=result.get("final_state") or {},
            )
            from agent.repositories.thread import ThreadRepository

            thread_row = await ThreadRepository(session).get(db_thread_id)
            if thread_row is not None:
                thread_row.last_message_at = datetime.now(UTC)
            await session.commit()

            return ChatResult(
                thread_id=db_thread_id,
                turn_id=turn_id,
                reply=result.get("reply", ""),
                new_thread=bool(result.get("new_thread_created")),
                decisions=result.get("decisions") or {},
                memory_degraded=bool(result.get("memory_degraded")),
                conversation_id=conv.id,
            )
