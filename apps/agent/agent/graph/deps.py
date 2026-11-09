from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from agent.config import Settings
from agent.model.decision import DecisionModel
from agent.model.query import QueryLLM
from agent.repositories.conversation import ConversationRepository
from agent.services.memory import MemoryService
from agent.services.threads import ThreadService


@dataclass
class GraphDeps:
    session: AsyncSession
    settings: Settings
    decision_model: DecisionModel
    query_llm: QueryLLM
    memory_service: MemoryService
    thread_service: ThreadService | None = None
    conversation_repo: ConversationRepository | None = None

    def get_thread_service(self) -> ThreadService:
        if self.thread_service is not None:
            return self.thread_service
        return ThreadService(self.session)

    def get_conversation_repo(self) -> ConversationRepository:
        if self.conversation_repo is not None:
            return self.conversation_repo
        return ConversationRepository(self.session)


def deps_from_config(config: dict) -> GraphDeps:
    return config["configurable"]["deps"]
