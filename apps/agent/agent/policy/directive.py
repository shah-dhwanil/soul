"""Per-turn directive builder and deterministic budget rules (spec §9-§14)."""

from collections.abc import Mapping, Sequence
from typing import Any

from agent.persona.constants.dials import Dials
from agent.persona.constants.modes import MODE_SPECS, Mode
from agent.persona.directive import TurnDirective
from agent.policy.modes import ModeDecision

CLOSING_SIGNALS: frozenset[str] = frozenset(
    {
        "ok", "okay", "k", "kk", "night", "nighty", "good night", "i'm good",
        "im good", "fine", "thanks", "thank you", "ty", "bye", "goodbye", "later",
        "cheers", "np", "no problem", "sure", "yeah", "yep", "done",
    }
)  # fmt: skip

_FALLBACK_BAND = (1, 40)
_FALLBACK_BUBBLES = 3
_NO_HUMOR_MODES = frozenset({Mode.LISTEN, Mode.GROUND, Mode.REPAIR, Mode.SAFETY})
_NO_CALLBACK_MODES = frozenset({Mode.LISTEN, Mode.GROUND, Mode.SAFETY, Mode.REPAIR})
_QUESTION_SENSITIVE_MODES = frozenset({Mode.BANTER, Mode.CELEBRATE, Mode.CHECK_IN})
_TRAIT_MODES = frozenset({Mode.EVERYDAY, Mode.BANTER})
_TRAILING_PUNCTUATION = " \t\n.,!?;:…-~'\"“”‘’"


def _is_closing_signal(message: str) -> bool:
    text = message.strip().lower().rstrip(_TRAILING_PUNCTUATION)
    return text in CLOSING_SIGNALS


def build_directive(
    *,
    mode_decision: ModeDecision,
    dials: Dials,
    stage: int,
    dependency_level: int,
    concern_tier: str,
    recent_turns: Sequence[Mapping[str, Any]],
    user_message: str,
    user_used_emoji: bool,
    user_started_pet_name: bool,
    distress_last_two_turns: bool,
    playful_last_four_turns: int,
    trait_available: bool,
    trait_pending_reaction: bool,
) -> TurnDirective:
    mode = mode_decision.mode
    codes: list[str] = []

    spec = MODE_SPECS.get(mode)
    if spec is not None:
        length_band = (spec.min_words, spec.max_words)
        max_bubbles = spec.max_bubbles
    else:  # SAFETY (or any unknown mode): plain fallback
        length_band = _FALLBACK_BAND
        max_bubbles = _FALLBACK_BUBBLES
        codes.append("length_band_fallback")

    # Question budget (§9)
    closing = _is_closing_signal(user_message)
    last_four = list(recent_turns)[-4:]
    asked_count = sum(1 for turn in last_four if turn.get("asked_question"))
    last_asked = bool(last_four) and bool(last_four[-1].get("asked_question"))
    question_allowed = True
    if closing:
        question_allowed = False
        codes.append("question_budget_closing_signal")
    if asked_count >= 2:
        question_allowed = False
        codes.append("question_budget_two_questions")
    if mode in _QUESTION_SENSITIVE_MODES and last_asked:
        question_allowed = False
        codes.append("question_budget_last_turn_asked")

    # Advice
    advice_allowed = mode in (Mode.DECIDE, Mode.UNSTUCK)
    if mode in (Mode.LISTEN, Mode.GROUND):
        codes.append(f"advice_denied_{mode.value}")

    # Humor
    humor_allowed = True
    if dials.humor == 0:
        humor_allowed = False
        codes.append("humor_denied_dial_zero")
    if distress_last_two_turns:
        humor_allowed = False
        codes.append("humor_denied_distress")
    if mode in _NO_HUMOR_MODES:
        humor_allowed = False
        codes.append(f"humor_denied_{mode.value}")

    # Callback
    callback_allowed = mode not in _NO_CALLBACK_MODES
    if not callback_allowed:
        codes.append(f"callback_denied_{mode.value}")

    # Trait
    trait_allowed = True
    if mode not in _TRAIT_MODES:
        trait_allowed = False
        codes.append(f"trait_denied_{mode.value}")
    if not trait_available:
        trait_allowed = False
        codes.append("trait_denied_unavailable")
    if trait_pending_reaction:
        trait_allowed = False
        codes.append("trait_denied_pending_reaction")

    return TurnDirective(
        mode=mode,
        length_band=length_band,
        max_bubbles=max_bubbles,
        question_allowed=question_allowed,
        advice_allowed=advice_allowed,
        humor_allowed=humor_allowed,
        callback_allowed=callback_allowed,
        trait_allowed=trait_allowed,
        concern_tier=concern_tier,
        dependency_level=dependency_level,
        stage=stage,
        closing_signal=closing,
        reason_codes=tuple(codes),
    )
