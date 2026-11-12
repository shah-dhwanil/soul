from datetime import UTC, datetime, timedelta

from agent.policy.dependency import compute_dependency_level, should_name_dependency


def _sig(sig: str, day: int):
    return {
        "signal": sig,
        "occurred_at": datetime(2026, 11, 1, tzinfo=UTC) + timedelta(days=day),
        "counts_toward_stage": True,
        "metadata": {},
    }


def test_no_signals_is_level_zero():
    assert compute_dependency_level(signals=(), low_baseline=False, now=datetime(2026, 11, 12, tzinfo=UTC)) == 0


def test_two_signals_is_level_one():
    signals = [_sig("d2", 0), _sig("d3", 1)]
    assert compute_dependency_level(signals=signals, low_baseline=False, now=datetime(2026, 11, 12, tzinfo=UTC)) == 1


def test_single_signal_is_level_zero():
    assert compute_dependency_level(signals=[_sig("d2", 0)], low_baseline=False, now=datetime(2026, 11, 12, tzinfo=UTC)) == 0


def test_d5_alone_is_level_two():
    assert compute_dependency_level(signals=[_sig("d5", 0)], low_baseline=False, now=datetime(2026, 11, 12, tzinfo=UTC)) == 2


def test_old_signals_expire():
    signals = [_sig("d2", 0), _sig("d3", 1)]
    assert compute_dependency_level(signals=signals, low_baseline=False, now=datetime(2027, 6, 1, tzinfo=UTC)) == 0


def test_level_two_line_is_rate_limited_to_two_months():
    now = datetime(2026, 11, 12, tzinfo=UTC)
    assert should_name_dependency(level=2, last_level2_at=None, now=now) is True
    assert should_name_dependency(level=2, last_level2_at=now - timedelta(days=10), now=now) is False
    assert should_name_dependency(level=2, last_level2_at=now - timedelta(days=70), now=now) is True
