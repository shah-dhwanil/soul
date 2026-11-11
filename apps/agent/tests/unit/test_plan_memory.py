import pytest
from unittest.mock import AsyncMock

from agent.config import Settings
from agent.graph.deps import GraphDeps
from agent.graph.nodes import plan_memory
from agent.graph.state import TurnState


@pytest.mark.asyncio
async def test_plan_memory_runs_when_clef_memory_false() -> None:
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        DATABASE__CHECKPOINTER_DATABASE_URL="postgresql://u:p@localhost/db",
        GROQ_API_KEY="x",
        CF_ACCOUNT_ID="a",
        CF_AI_API_TOKEN="t",
    )
    query_llm = AsyncMock()
    query_llm.get_queries = AsyncMock(return_value=["job interview", "interview schedule"])
    deps = GraphDeps(
        session=AsyncMock(),
        settings=settings,
        decision_model=AsyncMock(),
        query_llm=query_llm,
        memory_service=AsyncMock(),
        conversation_repo=AsyncMock(),
        thread_service=AsyncMock(),
    )
    config = {"configurable": {"deps": deps}}
    state = TurnState(
        user_message="Nothing much. Just my interview got preponed to this friday",
        memory_required=False,
        pipeline_history=[],
        turn_id="test-turn",
    )
    out = await plan_memory(state, config)
    query_llm.get_queries.assert_awaited_once_with(
        state["user_message"],
        [],
    )
    assert out["memory_queries"] == ["job interview", "interview schedule"]
