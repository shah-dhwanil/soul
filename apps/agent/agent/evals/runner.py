"""Run synthetic scenarios through TurnService and LLM judge."""

import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from agent.evals.judge import JudgeResult, ReplyJudge
from agent.evals.scenarios import CONVERSATION_SCENARIOS, ConversationScenario
from agent.history import PriorTurn
from agent.services.turns import ChatResult, TurnService

logger = logging.getLogger(__name__)


@dataclass
class TurnEvalResult:
    user_message: str
    reply: str
    chat: ChatResult
    judge: JudgeResult


@dataclass
class ScenarioEvalResult:
    scenario_id: str
    user_id: str
    turns: list[TurnEvalResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(t.judge.passed for t in self.turns)


@dataclass
class EvalReport:
    results: list[ScenarioEvalResult]

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    def summary_lines(self) -> list[str]:
        lines = [
            f"Eval pass rate: {self.pass_rate:.0%} ({sum(1 for r in self.results if r.passed)}/{len(self.results)} scenarios)",
        ]
        for sc in self.results:
            mark = "PASS" if sc.passed else "FAIL"
            lines.append(f"  [{mark}] {sc.scenario_id}")
            for i, turn in enumerate(sc.turns, 1):
                tmark = "ok" if turn.judge.passed else "FAIL"
                lines.append(
                    f"    turn {i} [{tmark}] score={turn.judge.score:.1f} "
                    f"user={turn.user_message[:50]!r}"
                )
                if turn.judge.verdict.violations:
                    lines.append(f"      violations: {turn.judge.verdict.violations}")
        return lines


async def seed_prior_turns(
    *,
    turn_service: TurnService,
    user_id: str,
    prior: tuple[PriorTurn, ...],
) -> None:
    await turn_service.seed_history(user_id, prior)


async def run_scenario(
    *,
    turn_service: TurnService,
    judge: ReplyJudge,
    scenario: ConversationScenario,
    user_id: str | None = None,
) -> ScenarioEvalResult:
    uid = user_id or f"eval-{scenario.id}-{uuid.uuid4().hex[:8]}"
    logger.info("eval scenario=%s user_id=%s", scenario.id, uid)

    if scenario.seed_prior:
        await seed_prior_turns(
            turn_service=turn_service, user_id=uid, prior=scenario.seed_prior
        )

    prior_chain: list[PriorTurn] = list(scenario.seed_prior)
    turn_results: list[TurnEvalResult] = []

    for eval_turn in scenario.turns:
        chat = await turn_service.handle_turn(uid, eval_turn.user_message)
        jr = await judge.evaluate(
            user_message=eval_turn.user_message,
            reply=chat.reply,
            turn=eval_turn,
            prior=tuple(prior_chain),
            decisions=chat.decisions,
        )
        turn_results.append(
            TurnEvalResult(
                user_message=eval_turn.user_message,
                reply=chat.reply,
                chat=chat,
                judge=jr,
            )
        )
        prior_chain.append(
            PriorTurn(eval_turn.user_message, chat.reply)
        )

    return ScenarioEvalResult(scenario_id=scenario.id, user_id=uid, turns=turn_results)


async def run_eval_suite(
    *,
    turn_service: TurnService,
    judge: ReplyJudge,
    scenarios: tuple[ConversationScenario, ...] = CONVERSATION_SCENARIOS,
) -> EvalReport:
    results: list[ScenarioEvalResult] = []
    for scenario in scenarios:
        results.append(
            await run_scenario(
                turn_service=turn_service,
                judge=judge,
                scenario=scenario,
            )
        )
    report = EvalReport(results=results)
    for line in report.summary_lines():
        logger.info(line)
    return report


# Type alias for tests that inject a fake turn handler
TurnHandler = Callable[[str, str], Awaitable[ChatResult]]
