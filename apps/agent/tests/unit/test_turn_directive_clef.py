from agent.persona.context import build_turn_directive

# Minimal Clef payload (shared shape with test_clef_flash_parsing).
_CLEF_FLASH_GUJARATI_TURN = {
    "answers": {
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
    }
}


def test_turn_directive_includes_clef_emotion_labels() -> None:
    directive = build_turn_directive({"raw": _CLEF_FLASH_GUJARATI_TURN})
    assert "neutral" in directive
    assert "direct" in directive
