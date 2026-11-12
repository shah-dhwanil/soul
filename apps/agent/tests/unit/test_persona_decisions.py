from agent.decision_parsing import parse_persona_signals


def _clef(answers: dict) -> dict:
    return {"answers": answers}


def test_parses_choice_answers():
    raw = _clef(
        {
            "concern_tier": {
                "type": "choice",
                "probabilities": {"normal": 0.1, "concern": 0.7, "acute": 0.2},
            },
            "register": {
                "type": "choice",
                "probabilities": {"playful": 0.8, "serious": 0.1, "neutral": 0.1},
            },
            "situation": {
                "type": "choice",
                "probabilities": {
                    "everyday_smalltalk": 0.05,
                    "venting": 0.05,
                    "thinking_aloud": 0.05,
                    "asking_decision": 0.05,
                    "overwhelmed": 0.05,
                    "good_news": 0.05,
                    "banter": 0.7,
                    "angry_at_wren": 0.05,
                    "spiraling": 0.05,
                },
            },
        }
    )
    signals = parse_persona_signals(raw)
    assert signals.concern_tier == "concern"
    assert signals.register == "playful"
    assert signals.situation == "banter"
    assert signals.degraded is False


def test_missing_answers_fail_open_to_normal():
    signals = parse_persona_signals({"answers": {}})
    assert signals.concern_tier == "normal"
    assert signals.register == "neutral"
    assert signals.situation == "everyday_smalltalk"
    assert signals.degraded is True


def test_malformed_answers_fail_open_to_normal():
    signals = parse_persona_signals(
        _clef({"concern_tier": {"type": "choice", "probabilities": "nonsense"}})
    )
    assert signals.concern_tier == "normal"
    assert signals.degraded is True


def test_never_raises_on_empty_payload():
    signals = parse_persona_signals({})
    assert signals.degraded is True
