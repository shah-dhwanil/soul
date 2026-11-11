"""Regression: real Clef-flash payload shape from production."""

from agent.decision_parsing import (
    clef_score_label,
    parse_thread_and_memory,
)

CLEF_FLASH_GUJARATI_TURN = {
    "model": "clef-flash",
    "answers": {
        "thread_continue": {"type": "noul", "noul": 0.85},
        "recent_context_required": {"type": "noul", "noul": 0.1691},
        "memory_required": {"type": "noul", "noul": 0.147},
        "user_emotion": {
            "type": "score",
            "score": 0.3325,
            "legend": {
                "0": "neutral",
                "1": "happy",
                "2": "sad",
                "3": "anxious",
                "4": "frustrated",
            },
            "probabilities": {
                "0": 0.8882,
                "1": 0.0215,
                "2": 0.0185,
                "3": 0.0132,
                "4": 0.0586,
            },
        },
        "agent_emotion": {
            "type": "score",
            "score": 1.9691,
            "legend": {
                "0": "warm",
                "1": "calm",
                "2": "playful",
                "3": "direct",
                "4": "supportive",
            },
            "probabilities": {
                "0": 0.1175,
                "1": 0.2292,
                "2": 0.2672,
                "3": 0.3388,
                "4": 0.0473,
            },
        },
    },
}


CLEF_FLASH_INTERVIEW_PREPONED = {
    "model": "clef-flash",
    "answers": {
        "thread_continue": {"type": "noul", "noul": 0.728},
        "recent_context_required": {"type": "noul", "noul": 0.1492},
        "memory_required": {"type": "noul", "noul": 0.0499},
    },
}


def test_interview_preponed_trace_clef_memory_still_low() -> None:
    inject, split, memory = parse_thread_and_memory(
        CLEF_FLASH_INTERVIEW_PREPONED, memory_threshold=0.35
    )
    assert inject is False
    assert split is False
    assert memory is False


def test_casual_greeting_does_not_inject_or_require_memory() -> None:
    inject, split, memory = parse_thread_and_memory(CLEF_FLASH_GUJARATI_TURN)
    assert inject is False
    assert split is False
    assert memory is False


def test_clef_score_labels_from_probabilities() -> None:
    answers = CLEF_FLASH_GUJARATI_TURN["answers"]
    assert clef_score_label(answers["user_emotion"]) == "neutral"
    assert clef_score_label(answers["agent_emotion"]) == "direct"
