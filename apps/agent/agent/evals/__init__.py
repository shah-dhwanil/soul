"""Synthetic conversations and LLM-as-judge evaluation."""

from agent.evals.runner import EvalReport, run_eval_suite
from agent.evals.scenarios import CONVERSATION_SCENARIOS, ConversationScenario

__all__ = [
    "CONVERSATION_SCENARIOS",
    "ConversationScenario",
    "EvalReport",
    "run_eval_suite",
]
