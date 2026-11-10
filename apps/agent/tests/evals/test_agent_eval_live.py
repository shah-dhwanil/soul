"""Live end-to-end eval — skipped unless RUN_AGENT_EVAL=1."""

import os

import pytest
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

from agent.config import get_settings
from agent.evals.judge import ReplyJudge
from agent.evals.runner import run_scenario
from agent.evals.scenarios import CONVERSATION_SCENARIOS
from agent.model.decision import DecisionModel
from agent.model.query import QueryLLM
from agent.pg.session import create_engine, create_session_factory
from agent.services.memory import MemoryService
from agent.services.turns import TurnService

pytestmark = pytest.mark.eval


def _live_enabled() -> bool:
    return os.getenv("RUN_AGENT_EVAL", "").strip() in {"1", "true", "yes"}


@pytest.fixture
async def turn_service():
    load_dotenv()
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    svc = TurnService(
        settings=settings,
        session_factory=factory,
        checkpointer=MemorySaver(),
        decision_model=DecisionModel(settings),
        query_llm=QueryLLM(settings),
        memory_service=MemoryService(settings),
    )
    yield svc
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.skipif(not _live_enabled(), reason="Set RUN_AGENT_EVAL=1 to run live eval")
async def test_gujarati_greeting_live(turn_service: TurnService) -> None:
    scenario = next(s for s in CONVERSATION_SCENARIOS if s.id == "gujarati_casual_greeting")
    judge = ReplyJudge(get_settings())
    result = await run_scenario(
        turn_service=turn_service,
        judge=judge,
        scenario=scenario,
    )
    assert result.passed, result.turns[0].judge.verdict.violations
