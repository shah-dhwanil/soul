"""LLM-as-judge for Wren reply quality."""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, ConfigDict, Field

from agent.config import Settings
from agent.evals.scenarios import EvalTurn
from agent.history import PriorTurn
from agent.persona.constants.banned import BANNED_PHRASES

logger = logging.getLogger(__name__)

JUDGE_SYSTEM = """\
You are an impartial evaluator for Wren, a texting-friend companion (not therapy).
Score the ASSISTANT reply only, using the rubric and constraints provided.

Return JSON only with this shape:
{
  "pass": boolean,
  "score": number from 0 to 10,
  "reasoning": string (2-4 sentences),
  "violations": string[] (specific issues; empty if none)
}

pass is true only if score >= 7 and no hard constraint was broken.
Hard failures: banned stock phrases from the list, obvious therapy/coach mode when
rubrics forbids it, wrong language register when rubric requires matching user language,
more questions than allowed, or claiming to miss/love the user.
"""


class JudgeVerdict(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pass_: bool = Field(alias="pass")
    score: float = Field(ge=0, le=10)
    reasoning: str
    violations: list[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.pass_


def _count_questions(text: str) -> int:
    return text.count("?")


def _hard_constraint_failures(
    reply: str, turn: EvalTurn
) -> list[str]:
    failures: list[str] = []
    lower = reply.lower()
    for phrase in turn.must_not_contain:
        if phrase.lower() in lower:
            failures.append(f"contains forbidden phrase: {phrase!r}")
    for chunk in (
        "I hear you",
        "I understand",
        "You've got this",
        "I'm so proud",
        "I missed you",
    ):
        if chunk.lower() in lower:
            failures.append(f"banned phrase: {chunk}")
    if turn.max_questions is not None:
        qs = _count_questions(reply)
        if qs > turn.max_questions:
            failures.append(f"too many questions ({qs} > {turn.max_questions})")
    return failures


def parse_judge_json(content: str) -> dict[str, Any] | None:
    match = re.search(r"\{[\s\S]*\}", content.strip())
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


@dataclass(frozen=True)
class JudgeResult:
    verdict: JudgeVerdict
    hard_failures: tuple[str, ...]
    passed: bool

    @property
    def score(self) -> float:
        return self.verdict.score


class ReplyJudge:
    def __init__(self, settings: Settings) -> None:
        model = settings.groq_agent_model
        self._llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=model,
            temperature=0.0,
        )

    async def evaluate(
        self,
        *,
        user_message: str,
        reply: str,
        turn: EvalTurn,
        prior: tuple[PriorTurn, ...] = (),
        decisions: dict[str, Any] | None = None,
    ) -> JudgeResult:
        hard = _hard_constraint_failures(reply, turn)
        history = "\n".join(
            f"user: {p.user_message}\nassistant: {p.agent_response}" for p in prior
        )
        decision_note = json.dumps(decisions, default=str)[:1500] if decisions else "{}"
        user_block = f"""Rubric:
{turn.rubric}

Banned phrase reference (non-exhaustive):
{", ".join(BANNED_PHRASES)[:800]}

Prior chat (may be empty):
{history or "(none)"}

User message:
{user_message}

Assistant reply to evaluate:
{reply}

Pipeline metadata (for context only, do not grade the pipeline):
{decision_note}
"""
        response = await self._llm.ainvoke(
            [SystemMessage(content=JUDGE_SYSTEM), HumanMessage(content=user_block)]
        )
        raw = parse_judge_json(str(response.content))
        if raw is None:
            verdict = JudgeVerdict(
                **{
                    "pass": False,
                    "score": 0.0,
                    "reasoning": "Judge returned unparseable JSON.",
                    "violations": ["judge_parse_error"],
                }
            )
        else:
            try:
                verdict = JudgeVerdict.model_validate(raw)
            except Exception as exc:  # noqa: BLE001
                verdict = JudgeVerdict(
                    **{
                        "pass": False,
                        "score": 0.0,
                        "reasoning": f"Judge schema error: {exc}",
                        "violations": ["judge_schema_error"],
                    }
                )

        passed = verdict.passed and not hard
        if hard:
            verdict.violations = list(verdict.violations) + hard
        logger.info(
            "judge pass=%s score=%.1f user=%r violations=%s",
            passed,
            verdict.score,
            user_message[:40],
            verdict.violations,
        )
        return JudgeResult(verdict=verdict, hard_failures=tuple(hard), passed=passed)
