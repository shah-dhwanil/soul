"""Prose renderers for the persona layers. No digits, field labels, or seed names."""

from collections.abc import Sequence

from agent.persona.constants.dials import Dials
from agent.persona.constants.temperaments import Temperament

_STAGE_PERMISSIONS = {
    1: (
        "You are still getting to know them. Hedge any interpretation, for example "
        "'you might be reading this wrong, but...' or 'I could be reading too much into it'. "
        "Stay with what they actually said and do not name patterns for them."
    ),
    2: (
        "You can be direct about patterns they have named themselves. Point back to their own "
        "words, plainly and without a lecture, and leave room for them to correct you."
    ),
    3: (
        "You can be direct and gentle about patterns they have lived. Say what you have "
        "noticed over time, with care, and let them decide what to do with it."
    ),
}


def render_temperament(temperament: Temperament) -> str:
    return (
        f"Your humour runs to {temperament.humor.lower()}, and you are curious about "
        f"{temperament.curiosity[0].lower() + temperament.curiosity[1:]}. "
        f"When you push back: {temperament.pushback[0].lower() + temperament.pushback[1:]}. "
        f"Your pace is {temperament.pace.lower()}."
    )


def _humor_phrase(humor: int) -> str:
    if humor <= 0:
        return "no humour"
    if humor <= 4:
        return "dry humour, and none of it if they are hurting"
    return "playful, and none of it if they are hurting"


def render_dials(dials: Dials, *, seed: Temperament | None = None) -> str:
    parts = [
        "casual" if dials.formality <= 2 else "a little more formal",
        "warm" if dials.warmth < 7 else "warm, and shows it",
        "willing to disagree once, with a reason",
        _humor_phrase(dials.humor),
        "observes more than it interviews",
    ]
    return "; ".join(parts) + "."


def render_stage_permissions(stage: int) -> str:
    return _STAGE_PERMISSIONS[max(1, min(3, stage))]


def render_active_traits(traits: Sequence[str]) -> str:
    if not traits:
        return "No shared language yet."
    return "Shared language you can use this turn: " + "; ".join(traits) + "."
