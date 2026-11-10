#!/usr/bin/env python3
"""Run synthetic conversation evals with LLM-as-judge (live APIs + Postgres)."""

import argparse
import asyncio
import sys

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

from agent.config import get_settings
from agent.evals.judge import ReplyJudge
from agent.evals.runner import run_eval_suite, run_scenario
from agent.evals.scenarios import CONVERSATION_SCENARIOS, ConversationScenario
from agent.logging_config import configure_logging
from agent.model.decision import DecisionModel
from agent.model.query import QueryLLM
from agent.pg.session import create_engine, create_session_factory
from agent.services.memory import MemoryService
from agent.services.turns import TurnService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="End-to-end Wren agent eval")
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenario_ids",
        help="Run only these scenario ids (repeatable)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after first failing scenario",
    )
    return parser.parse_args()


async def _main() -> int:
    load_dotenv()
    configure_logging()
    args = _parse_args()
    settings = get_settings()

    scenarios: tuple[ConversationScenario, ...] = CONVERSATION_SCENARIOS
    if args.scenario_ids:
        wanted = set(args.scenario_ids)
        scenarios = tuple(s for s in CONVERSATION_SCENARIOS if s.id in wanted)
        missing = wanted - {s.id for s in scenarios}
        if missing:
            print(f"Unknown scenario ids: {sorted(missing)}", file=sys.stderr)
            return 2

    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    turn_service = TurnService(
        settings=settings,
        session_factory=session_factory,
        checkpointer=MemorySaver(),
        decision_model=DecisionModel(settings),
        query_llm=QueryLLM(settings),
        memory_service=MemoryService(settings),
    )
    judge = ReplyJudge(settings)

    exit_code = 0
    try:
        if args.fail_fast:
            for scenario in scenarios:
                result = await run_scenario(
                    turn_service=turn_service,
                    judge=judge,
                    scenario=scenario,
                )
                mark = "PASS" if result.passed else "FAIL"
                print(f"\n=== [{mark}] {scenario.id} ===")
                for i, t in enumerate(result.turns, 1):
                    print(f"\n--- turn {i} ---")
                    print(f"user: {t.user_message}")
                    print(f"reply: {t.reply}")
                    print(
                        f"judge: pass={t.judge.passed} score={t.judge.score:.1f} "
                        f"reason: {t.judge.verdict.reasoning}"
                    )
                if not result.passed:
                    return 1
            print("\nAll scenarios passed.")
            return 0

        report = await run_eval_suite(
            turn_service=turn_service,
            judge=judge,
            scenarios=scenarios,
        )
        for sc in report.results:
            mark = "PASS" if sc.passed else "FAIL"
            print(f"\n=== [{mark}] {sc.scenario_id} ===")
            for i, t in enumerate(sc.turns, 1):
                print(f"user: {t.user_message}")
                print(f"reply: {t.reply[:500]}")
                print(f"judge score={t.judge.score:.1f} pass={t.judge.passed}")
        print("\n" + "\n".join(report.summary_lines()))
        exit_code = 0 if report.passed else 1
    finally:
        await engine.dispose()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
