import pytest

from agent.evals.judge import (
    ReplyJudge,
    _hard_constraint_failures,
    parse_judge_json,
)
from agent.evals.scenarios import EvalTurn


def test_parse_judge_json() -> None:
    raw = parse_judge_json('{"pass": true, "score": 8, "reasoning": "ok", "violations": []}')
    assert raw is not None
    assert raw["pass"] is True


def test_hard_constraint_banned_and_questions() -> None:
    turn = EvalTurn(
        user_message="hi",
        rubric="test",
        must_not_contain=("small step",),
        max_questions=1,
    )
    fails = _hard_constraint_failures(
        "I hear you. What's up? What else?",
        turn,
    )
    assert any("banned phrase" in f for f in fails)
    assert any("questions" in f for f in fails)


@pytest.mark.asyncio
async def test_judge_evaluate_with_mock_llm(monkeypatch) -> None:
    from agent.config import Settings

    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        DATABASE__CHECKPOINTER_DATABASE_URL="postgresql://u:p@localhost/db",
        GROQ_API_KEY="x",
        CF_ACCOUNT_ID="a",
        CF_AI_API_TOKEN="t",
    )
    judge = ReplyJudge(settings)

    class FakeMsg:
        content = (
            '{"pass": true, "score": 9, "reasoning": "Casual and fine.", "violations": []}'
        )

    class FakeLLM:
        async def ainvoke(self, messages):  # noqa: ANN001
            return FakeMsg()

    judge._llm = FakeLLM()
    turn = EvalTurn(
        user_message="Su kare che bro",
        rubric="casual greeting",
        must_not_contain=("small step",),
    )
    result = await judge.evaluate(
        user_message=turn.user_message,
        reply="Bas bro, su che!",
        turn=turn,
    )
    assert result.passed
