"""Parse Cloudflare Clef decision API payloads."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _noul_yes_probability(answer: Any) -> float:
    """P(yes) for Clef ``noul`` questions (0–1)."""
    if not isinstance(answer, dict):
        return 0.5
    for key in ("noul", "probability_yes", "yes", "probability"):
        if key in answer:
            try:
                return float(answer[key])
            except (TypeError, ValueError):
                continue
    if "label" in answer and isinstance(answer.get("confidence"), (int, float)):
        if str(answer["label"]).lower() in {"yes", "true"}:
            return float(answer["confidence"])
        return 1.0 - float(answer["confidence"])
    logger.warning("Could not parse noul answer: %s", answer)
    return 0.5


def clef_score_label(answer: Any) -> str | None:
    """Best label from Clef ``score`` answers (flash legend + score or probabilities)."""
    if not isinstance(answer, dict) or answer.get("type") != "score":
        return None
    legend = answer.get("legend") or {}
    if not legend:
        return answer.get("label") if isinstance(answer.get("label"), str) else None

    probs = answer.get("probabilities")
    if isinstance(probs, dict) and probs:
        best_key = max(probs, key=lambda k: float(probs[k]))
        label = legend.get(str(best_key)) or legend.get(best_key)
        if label:
            return str(label)

    if "score" in answer:
        try:
            idx = int(round(float(answer["score"])))
            label = legend.get(str(idx)) or legend.get(idx)
            if label:
                return str(label)
        except (TypeError, ValueError):
            pass
    return None


def parse_thread_and_memory(
    clef_result: dict[str, Any],
    *,
    inject_threshold: float = 0.5,
    split_threshold: float = 0.2,
    memory_threshold: float = 0.5,
) -> tuple[bool, bool, bool]:
    """Return inject_previous_chat, split_thread, memory_required."""
    answers = clef_result.get("answers") or {}
    thread_answer = answers.get("thread_continue", {})
    recent_answer = answers.get("recent_context_required", {})
    memory_answer = answers.get("memory_required", {})

    p_continue = _noul_yes_probability(thread_answer)
    p_recent = _noul_yes_probability(recent_answer)
    p_memory = _noul_yes_probability(memory_answer)
    inject_previous_chat = p_recent >= inject_threshold
    split_thread = p_continue < split_threshold
    memory_required = p_memory >= memory_threshold

    logger.info(
        "Clef parse: p_continue=%.4f p_recent=%.4f p_memory=%.4f "
        "inject=%s split=%s memory=%s",
        p_continue,
        p_recent,
        p_memory,
        inject_previous_chat,
        split_thread,
        memory_required,
    )
    return inject_previous_chat, split_thread, memory_required
