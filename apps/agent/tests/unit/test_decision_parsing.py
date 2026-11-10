from agent.decision_parsing import parse_thread_and_memory


def test_parse_noul_key_clef_flash() -> None:
    raw = {
        "answers": {
            "thread_continue": {"type": "noul", "noul": 0.9},
            "memory_required": {"type": "noul", "noul": 0.1},
        }
    }
    inject, split, memory = parse_thread_and_memory(raw, continue_threshold=0.5)
    assert inject is True
    assert split is False
    assert memory is False


def test_parse_thread_continue_yes_injects_history() -> None:
    raw = {
        "answers": {
            "thread_continue": {"probability_yes": 0.9},
            "memory_required": {"probability_yes": 0.1},
        }
    }
    inject, split, memory = parse_thread_and_memory(raw, continue_threshold=0.5)
    assert inject is True
    assert split is False
    assert memory is False


def test_parse_thread_continue_no_splits() -> None:
    raw = {
        "answers": {
            "thread_continue": {"probability_yes": 0.2},
            "memory_required": {"probability_yes": 0.85},
        }
    }
    inject, split, memory = parse_thread_and_memory(raw, continue_threshold=0.5)
    assert inject is False
    assert split is True
    assert memory is True
