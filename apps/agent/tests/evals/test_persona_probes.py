# apps/agent/tests/evals/test_persona_probes.py
from agent.evals.checks import run_deterministic_checks
from agent.evals.scenarios import PROBE_SCENARIOS


def test_fourteen_probes_exist():
    assert len(PROBE_SCENARIOS) == 14


def test_every_probe_has_a_unique_id():
    ids = [p.id for p in PROBE_SCENARIOS]
    assert len(ids) == len(set(ids))


def test_concern_probe_includes_the_buried_anyway_case():
    probe = next(p for p in PROBE_SCENARIOS if p.id == "concern_tier_routing")
    joined = " ".join(t.user_message for t in probe.turns)
    assert "anyway" in joined


def test_deterministic_checks_catch_a_banned_phrase():
    checks = run_deterministic_checks(
        user_message="hi",
        reply="I hear you. How are you?",
        mode="everyday",
        concern_tier="normal",
        directive=None,
    )
    assert not all(c.passed for c in checks)
