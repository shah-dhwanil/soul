from datetime import UTC, datetime, timedelta

from agent.policy.stage import compute_stage


def _signal(sig: str, day: int, counts: bool = True):
    return {
        "signal": sig,
        "occurred_at": datetime(2026, 11, 1, tzinfo=UTC) + timedelta(days=day),
        "counts_toward_stage": counts,
        "metadata": {},
    }


def test_stage_one_by_default():
    assert compute_stage(signals=(), exchange_count=0, dependency_level=0, frozen_at=None, now=datetime(2026, 11, 12, tzinfo=UTC)) == 1


def test_stage_two_requires_three_signals_twice_over_five_days():
    signals = []
    for sig in ("s1", "s5", "s6"):
        for day in range(5):
            signals.append(_signal(sig, day))
    stage = compute_stage(
        signals=signals,
        exchange_count=60,
        dependency_level=0,
        frozen_at=None,
        now=datetime(2026, 11, 12, tzinfo=UTC),
    )
    assert stage == 2


def test_stage_two_needs_fifty_exchanges():
    signals = []
    for sig in ("s1", "s5", "s6"):
        for day in (0, 1):
            signals.append(_signal(sig, day))
    assert compute_stage(
        signals=signals,
        exchange_count=10,
        dependency_level=0,
        frozen_at=None,
        now=datetime(2026, 11, 12, tzinfo=UTC),
    ) == 1


def test_dependency_level_two_freezes_advancement():
    signals = []
    for sig in ("s1", "s5", "s6"):
        for day in (0, 1):
            signals.append(_signal(sig, day))
    assert compute_stage(
        signals=signals,
        exchange_count=200,
        dependency_level=2,
        frozen_at=datetime(2026, 11, 10, tzinfo=UTC),
        now=datetime(2026, 11, 12, tzinfo=UTC),
    ) == 1


def test_signals_marked_excluded_do_not_count():
    signals = [_signal("s1", 0, counts=False) for _ in range(4)]
    assert compute_stage(
        signals=signals,
        exchange_count=200,
        dependency_level=0,
        frozen_at=None,
        now=datetime(2026, 11, 12, tzinfo=UTC),
    ) == 1
