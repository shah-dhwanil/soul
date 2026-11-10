from agent.evals.scenarios import CONVERSATION_SCENARIOS


def test_scenarios_are_unique_and_non_empty() -> None:
    ids = [s.id for s in CONVERSATION_SCENARIOS]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 3
    for s in CONVERSATION_SCENARIOS:
        assert s.turns
        for t in s.turns:
            assert t.user_message.strip()
            assert t.rubric.strip()
