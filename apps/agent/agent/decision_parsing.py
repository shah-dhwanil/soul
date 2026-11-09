"""Parse Cloudflare Clef decision API payloads."""

from typing import Any


def _noul_yes_probability(answer: Any) -> float:
    if not isinstance(answer, dict):
        return 0.5
    for key in ("probability_yes", "yes", "probability"):
        if key in answer:
            try:
                return float(answer[key])
            except (TypeError, ValueError):
                continue
    if "label" in answer and isinstance(answer.get("confidence"), (int, float)):
        if str(answer["label"]).lower() in {"yes", "true"}:
            return float(answer["confidence"])
        return 1.0 - float(answer["confidence"])
    return 0.5


def parse_thread_and_memory(
    clef_result: dict[str, Any], *, continue_threshold: float = 0.5
) -> tuple[bool, bool, bool]:
    """Return inject_previous_chat, split_thread, memory_required."""
    answers = clef_result.get("answers") or {}
    thread_answer = answers.get("thread_continue", {})
    memory_answer = answers.get("memory_required", {})

    needs_history = _noul_yes_probability(thread_answer) >= continue_threshold
    inject_previous_chat = needs_history
    split_thread = not needs_history
    memory_required = _noul_yes_probability(memory_answer) >= continue_threshold
    return inject_previous_chat, split_thread, memory_required
