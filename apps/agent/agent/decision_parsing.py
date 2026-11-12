"""Parse Cloudflare Clef decision API payloads."""

import logging
from dataclasses import dataclass
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


CONCERN_TIERS = ("normal", "concern", "acute")
REGISTERS = ("playful", "serious", "neutral")
SITUATIONS = (
    "everyday_smalltalk",
    "venting",
    "thinking_aloud",
    "asking_decision",
    "overwhelmed",
    "good_news",
    "banter",
    "angry_at_wren",
    "spiraling",
)


@dataclass(frozen=True)
class PersonaSignals:
    concern_tier: str
    register: str
    situation: str
    concern_confidence: float
    register_confidence: float
    situation_confidence: float
    degraded: bool


def _choice_winner(
    answers: dict[str, Any],
    question_id: str,
    allowed: tuple[str, ...],
) -> tuple[str, float] | None:
    """Return (key, probability) of the top choice, or None if unusable."""
    answer = answers.get(question_id)
    if not isinstance(answer, dict):
        return None
    probs = answer.get("probabilities")
    if not isinstance(probs, dict) or not probs:
        return None
    try:
        scored = {str(k): float(v) for k, v in probs.items()}
    except (TypeError, ValueError):
        return None
    best = max(scored, key=lambda k: scored[k])
    if best not in allowed:
        return None
    return best, scored[best]


def parse_persona_signals(clef_result: dict[str, Any]) -> PersonaSignals:
    """Parse concern_tier, register, situation; fail open and never raise."""
    answers = clef_result.get("answers") if isinstance(clef_result, dict) else None
    if not isinstance(answers, dict):
        answers = {}

    degraded = False
    values: list[tuple[str, float]] = []
    for question_id, allowed, default in (
        ("concern_tier", CONCERN_TIERS, "normal"),
        ("register", REGISTERS, "neutral"),
        ("situation", SITUATIONS, "everyday_smalltalk"),
    ):
        winner = _choice_winner(answers, question_id, allowed)
        if winner is None:
            logger.warning("Could not parse persona answer: %s", question_id)
            degraded = True
            winner = (default, 0.0)
        values.append(winner)

    return PersonaSignals(
        concern_tier=values[0][0],
        register=values[1][0],
        situation=values[2][0],
        concern_confidence=values[0][1],
        register_confidence=values[1][1],
        situation_confidence=values[2][1],
        degraded=degraded,
    )
