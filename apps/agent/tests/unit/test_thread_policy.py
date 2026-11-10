import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from agent.config import Settings
from agent.graph.deps import GraphDeps
from agent.graph.nodes import apply_thread_policy
from agent.graph.state import TurnState
from agent.history import ChatTurn


@pytest.mark.asyncio
async def test_split_rotates_and_sets_generation_history() -> None:
    old_thread = uuid4()
    new_thread = uuid4()
    session = AsyncMock()
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        DATABASE__CHECKPOINTER_DATABASE_URL="postgresql://u:p@localhost/db",
        GROQ_API_KEY="x",
        CF_ACCOUNT_ID="a",
        CF_AI_API_TOKEN="t",
        split_generation_history_limit=10,
        pipeline_history_limit=5,
        min_turns_before_split=1,
    )

    conv_row = MagicMock()
    conv_row.user_message = "hi"
    conv_row.agent_response = "hello"
    repo = AsyncMock()
    repo.list_by_thread = AsyncMock(return_value=[conv_row])
    thread_service = AsyncMock()
    thread_service.rotate = AsyncMock(return_value=new_thread)

    deps = GraphDeps(
        session=session,
        settings=settings,
        decision_model=AsyncMock(),
        query_llm=AsyncMock(),
        memory_service=AsyncMock(),
        conversation_repo=repo,
        thread_service=thread_service,
    )

    state = TurnState(
        user_id="user-1",
        db_thread_id=str(old_thread),
        split_thread=True,
        inject_previous_chat=False,
    )
    config = {"configurable": {"deps": deps}}
    out = await apply_thread_policy(state, config)

    assert out["new_thread_created"] is True
    assert out["db_thread_id"] == str(new_thread)
    assert out["pipeline_history"] == []
    assert len(out["generation_history"]) == 1
    assert out["generation_history"][0].user_message == "hi"
    thread_service.rotate.assert_awaited_once()


@pytest.mark.asyncio
async def test_inject_loads_pipeline_history() -> None:
    thread_id = uuid4()
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        DATABASE__CHECKPOINTER_DATABASE_URL="postgresql://u:p@localhost/db",
        GROQ_API_KEY="x",
        CF_ACCOUNT_ID="a",
        CF_AI_API_TOKEN="t",
        pipeline_history_limit=5,
    )
    conv_row = MagicMock()
    conv_row.user_message = "a"
    conv_row.agent_response = "b"
    repo = AsyncMock()
    repo.list_recent_for_thread = AsyncMock(return_value=[conv_row])

    deps = GraphDeps(
        session=AsyncMock(),
        settings=settings,
        decision_model=AsyncMock(),
        query_llm=AsyncMock(),
        memory_service=AsyncMock(),
        conversation_repo=repo,
    )

    state = TurnState(
        user_id="u",
        db_thread_id=str(thread_id),
        split_thread=False,
        inject_previous_chat=True,
    )
    out = await apply_thread_policy(state, {"configurable": {"deps": deps}})
    assert out["pipeline_history"][0] == ChatTurn("a", "b")
    assert out["generation_history"] == out["pipeline_history"]


@pytest.mark.asyncio
async def test_split_suppressed_below_min_turns() -> None:
    thread_id = uuid4()
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        DATABASE__CHECKPOINTER_DATABASE_URL="postgresql://u:p@localhost/db",
        GROQ_API_KEY="x",
        CF_ACCOUNT_ID="a",
        CF_AI_API_TOKEN="t",
        min_turns_before_split=2,
    )
    conv_row = MagicMock()
    conv_row.user_message = "hi"
    conv_row.agent_response = "hello"
    repo = AsyncMock()
    repo.list_by_thread = AsyncMock(return_value=[conv_row])
    thread_service = AsyncMock()

    deps = GraphDeps(
        session=AsyncMock(),
        settings=settings,
        decision_model=AsyncMock(),
        query_llm=AsyncMock(),
        memory_service=AsyncMock(),
        conversation_repo=repo,
        thread_service=thread_service,
    )
    state = TurnState(
        user_id="u",
        db_thread_id=str(thread_id),
        split_thread=True,
        inject_previous_chat=False,
    )
    out = await apply_thread_policy(state, {"configurable": {"deps": deps}})
    assert out["new_thread_created"] is False
    assert out["db_thread_id"] == str(thread_id)
    thread_service.rotate.assert_not_awaited()
