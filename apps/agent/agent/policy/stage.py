"""Relationship stage computation (spec §11.2). Pure functions over signal mappings."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Stage2Threshold:
    min_signals: int = 3
    min_repeats_per_signal: int = 2
    min_distinct_days: int = 5
    min_exchanges: int = 50


@dataclass(frozen=True)
class Stage3Threshold:
    min_signals: int = 5
    min_distinct_days: int = 28
    min_exchanges: int = 150


STAGE_2_THRESHOLD = Stage2Threshold()
STAGE_3_THRESHOLD = Stage3Threshold()
REQUIRED_STAGE_3_SIGNALS: frozenset[str] = frozenset({"s2", "s4"})


def _get(signal: Any, key: str) -> Any:
    if isinstance(signal, Mapping):
        return signal.get(key)
    return getattr(signal, key, None)


def _code(signal: Any) -> str:
    value = _get(signal, "signal")
    return str(getattr(value, "value", value)).lower()


def signal_local_date(signal: Any) -> str:
    """Local calendar day (caller-resolved) or the UTC date as fallback."""
    metadata = _get(signal, "metadata") or {}
    local_date = metadata.get("local_date") if isinstance(metadata, Mapping) else None
    if local_date:
        return str(local_date)
    return _get(signal, "occurred_at").date().isoformat()


def compute_stage(
    *,
    signals: Sequence[Any],
    exchange_count: int,
    dependency_level: int,
    frozen_at: datetime | None,
    now: datetime,
) -> int:
    """Return stage 1, 2 or 3."""
    if dependency_level >= 2:
        return 1  # advancement frozen

    counted = []
    for sig in signals:
        if not _get(sig, "counts_toward_stage"):
            continue
        if frozen_at is not None and _get(sig, "occurred_at") >= frozen_at:
            continue  # logged during a freeze: stays excluded
        counted.append(sig)

    per_code: dict[str, int] = defaultdict(int)
    days: set[str] = set()
    for sig in counted:
        per_code[_code(sig)] += 1
        days.add(signal_local_date(sig))

    t3 = STAGE_3_THRESHOLD
    if (
        len(per_code) >= t3.min_signals
        and REQUIRED_STAGE_3_SIGNALS <= per_code.keys()
        and len(days) >= t3.min_distinct_days
        and exchange_count >= t3.min_exchanges
    ):
        return 3

    t2 = STAGE_2_THRESHOLD
    repeated = [c for c, n in per_code.items() if n >= t2.min_repeats_per_signal]
    if (
        len(repeated) >= t2.min_signals
        and len(days) >= t2.min_distinct_days
        and exchange_count >= t2.min_exchanges
    ):
        return 2
    return 1
