"""Leaning lifecycle state machine (spec §12.6). Pure; no DB access."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from agent.pg.models import LeaningStatus


class LeaningKind(str, Enum):
    HUMOR_STYLE = "humor_style"
    CURIOSITY_DOMAIN = "curiosity_domain"
    PUSHBACK_MANNER = "pushback_manner"


@dataclass(frozen=True)
class LeaningMutation:
    status: LeaningStatus
    promoted: bool
    retired: bool
    reason: str


def observe_leaning(
    *,
    kind: str,
    value: str,
    status: str,
    positive_count: int,
    negative_count: int,
    distinct_days: int,
    engagement_at_or_above_baseline: bool,
) -> LeaningMutation:
    current = LeaningStatus(status)

    def keep(reason: str) -> LeaningMutation:
        return LeaningMutation(current, False, False, reason)

    if current is LeaningStatus.RETIRED:
        return keep("retired leanings are never re-proposed")

    if current is not LeaningStatus.NOTICED and negative_count >= 2:
        return LeaningMutation(
            LeaningStatus.RETIRED, False, True, "two negative reactions"
        )

    if current is LeaningStatus.NOTICED:
        if kind == LeaningKind.HUMOR_STYLE.value:
            ok = positive_count >= 3 and negative_count <= 1 and distinct_days >= 3
        elif kind == LeaningKind.PUSHBACK_MANNER.value:
            ok = positive_count >= 2 and negative_count == 0
        else:
            ok = distinct_days >= 3 and engagement_at_or_above_baseline
        if ok:
            return LeaningMutation(
                LeaningStatus.CANDIDATE, True, False, "evidence threshold met"
            )
        return keep("insufficient evidence")

    if current is LeaningStatus.CANDIDATE:
        return LeaningMutation(LeaningStatus.TILT, True, False, "one-notch tilt")

    if current is LeaningStatus.TILT:
        if engagement_at_or_above_baseline:
            return LeaningMutation(
                LeaningStatus.ACTIVE, True, False, "engagement held during tilt"
            )
        return keep("engagement below baseline; tilt continues")

    return keep("no change")
