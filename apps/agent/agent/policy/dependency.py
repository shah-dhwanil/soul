"""Dependency drift level computation (spec §13). Pure functions over signal mappings."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any

from agent.policy.stage import signal_local_date

DEPENDENCY_WINDOW_DAYS = 28
DEPENDENCY_EXPIRY_DAYS = 42
LEVEL_2_REPEAT_DAYS = 60

D5 = "d5"
NO_ONE_ELSE = "no_one_else"
DISTRESS = "distress"  # Listen/Ground/concern exchange marker for a day


def _get(signal: Any, key: str) -> Any:
    if isinstance(signal, Mapping):
        return signal.get(key)
    return getattr(signal, key, None)


def _code(signal: Any) -> str:
    value = _get(signal, "signal")
    return str(getattr(value, "value", value)).lower()


def _explained(signal: Any) -> bool:
    metadata = _get(signal, "metadata") or {}
    return bool(isinstance(metadata, Mapping) and metadata.get("explained"))


def compute_dependency_level(
    *,
    signals: Sequence[Any],
    low_baseline: bool,
    now: datetime,
) -> int:
    """Return dependency level 0-3."""
    expiry = now - timedelta(days=DEPENDENCY_EXPIRY_DAYS)
    window = now - timedelta(days=DEPENDENCY_WINDOW_DAYS)
    live = [s for s in signals if _get(s, "occurred_at") >= expiry]

    codes_all = {_code(s) for s in live}
    if NO_ONE_ELSE in codes_all:
        return 3  # explicit statement

    in_window = [s for s in live if _get(s, "occurred_at") >= window]
    drift = {
        _code(s)
        for s in in_window
        if _code(s) not in (DISTRESS, NO_ONE_ELSE) and not _explained(s)
    }
    has_d5 = D5 in drift

    distress_days = {
        signal_local_date(s) for s in live if _code(s) == DISTRESS
    }
    distress = has_d5 or len(distress_days) >= 2

    if len(drift) >= 3 and distress:
        return 3
    if len(drift) >= 3 or has_d5:
        return 2
    if len(drift) >= 2 or low_baseline:
        return 1
    return 0


def should_name_dependency(
    *,
    level: int,
    last_level2_at: datetime | None,
    now: datetime,
) -> bool:
    """Level 2 may be said at most once every two months."""
    if level < 2:
        return False
    if last_level2_at is None:
        return True
    return now - last_level2_at >= timedelta(days=LEVEL_2_REPEAT_DAYS)
