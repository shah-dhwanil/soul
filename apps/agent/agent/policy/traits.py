"""Trait lifecycle state machine (spec §12.2). Pure; no DB access."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from agent.pg.models import TraitStatus


class TraitKind(str, Enum):
    SHARED_LANGUAGE = "shared_language"
    MILD_LEANING = "mild_leaning"
    DEEP_LEANING = "deep_leaning"
    RUNNING_JOKE = "running_joke"
    ROLE = "role"
    RITUAL = "ritual"


SENSITIVE_CATEGORIES: frozenset[str] = frozenset(
    {"health", "grief", "money", "relationship_conflict"}
)

_SENSITIVE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "health": (
        "health", "injury", "injured", "sick", "illness", "disease", "cancer",
        "surgery", "pain", "diagnosis", "doctor", "hospital", "medication",
        "therapy", "anxiety", "depression", "panic", "migraine", "chronic",
    ),
    "grief": (
        "grief", "grieving", "died", "death", "passed away", "funeral",
        "mourning", "bereaved", "miscarriage", "loss of",
    ),
    "money": (
        "money", "debt", "loan", "mortgage", "rent", "salary", "bankrupt",
        "broke", "savings", "afford", "bills", "credit card",
    ),
    "relationship_conflict": (
        "divorce", "breakup", "broke up", "separated", "cheating", "affair",
        "fight with", "argument with", "toxic", "abusive", "custody",
    ),
}

_PATTERNS = [
    re.compile(r"\b" + re.escape(k) + r"\b")
    for kws in _SENSITIVE_KEYWORDS.values()
    for k in kws
]

_TRIAL_MODES = frozenset({"everyday", "banter"})


@dataclass(frozen=True)
class TraitMutation:
    status: TraitStatus
    promoted: bool
    retired: bool
    reason: str


def trait_is_sensitive(label: str, quote: str) -> bool:
    text = f"{label} {quote}".lower()
    return any(p.search(text) for p in _PATTERNS)


def trial_allowed(mode: str) -> bool:
    return mode in _TRIAL_MODES


def observe_trait(
    *,
    kind: str,
    label: str,
    status: str,
    positive_count: int,
    negative_count: int,
    neutral_count: int,
    distinct_days: int,
    reaction: str | None,
    sensitive: bool,
) -> TraitMutation:
    current = TraitStatus(status)

    def keep(reason: str) -> TraitMutation:
        return TraitMutation(current, False, False, reason)

    if current is TraitStatus.RETIRED:
        return keep("retired traits are never re-proposed")

    if sensitive:
        return keep("sensitive traits never advance")

    if current in (TraitStatus.CANDIDATE, TraitStatus.ACTIVE, TraitStatus.TRIAL):
        if negative_count >= 2:
            return TraitMutation(
                TraitStatus.RETIRED, False, True, "two negative reactions"
            )

    if current is TraitStatus.NOTICED:
        seen = positive_count + negative_count + neutral_count
        if (
            reaction != "neutral"
            and positive_count >= 1
            and distinct_days >= 2
            and seen >= 2
        ):
            return TraitMutation(
                TraitStatus.CANDIDATE, True, False, "positive on 2+ days"
            )
        return keep("insufficient positive evidence")

    if current is TraitStatus.TRIAL:
        if reaction == "positive":
            return TraitMutation(TraitStatus.ACTIVE, True, False, "trial landed")
        if reaction == "neutral":
            if neutral_count >= 2:
                return TraitMutation(
                    TraitStatus.RETIRED, False, True, "trial ignored twice"
                )
            return TraitMutation(
                TraitStatus.CANDIDATE, False, False, "trial ignored once"
            )
        return keep("no trial outcome")

    return keep("no change")
