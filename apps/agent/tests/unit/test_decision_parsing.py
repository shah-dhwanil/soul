from agent.decision_parsing import parse_thread_and_memory


def test_parse_noul_key_clef_flash() -> None:
    raw = {
        "answers": {
            "thread_continue": {"type": "noul", "noul": 0.9},
            "recent_context_required": {"type": "noul", "noul": 0.9},
            "memory_required": {"type": "noul", "noul": 0.1},
        }
    }
    inject, split, memory = parse_thread_and_memory(raw)
    assert inject is True
    assert split is False
    assert memory is False


def test_parse_recent_context_injects_without_split() -> None:
    raw = {
        "answers": {
            "thread_continue": {"probability_yes": 0.9},
            "recent_context_required": {"probability_yes": 0.9},
            "memory_required": {"probability_yes": 0.1},
        }
    }
    inject, split, memory = parse_thread_and_memory(raw)
    assert inject is True
    assert split is False
    assert memory is False


def test_parse_middle_band_no_inject_no_split() -> None:
    raw = {
        "answers": {
            "thread_continue": {"probability_yes": 0.35},
            "recent_context_required": {"probability_yes": 0.2},
            "memory_required": {"probability_yes": 0.85},
        }
    }
    inject, split, memory = parse_thread_and_memory(raw)
    assert inject is False
    assert split is False
    assert memory is True


def test_parse_session_low_splits() -> None:
    raw = {
        "answers": {
            "thread_continue": {"probability_yes": 0.1},
            "recent_context_required": {"probability_yes": 0.2},
            "memory_required": {"probability_yes": 0.1},
        }
    }
    inject, split, memory = parse_thread_and_memory(raw)
    assert inject is False
    assert split is True
    assert memory is False
