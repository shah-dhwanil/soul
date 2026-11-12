"""Per-turn persona snapshot. Never log message content."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from typing import Any

from agent.persona.constants.dials import Dials, clamp_dials, narrow_rejected_combinations
from agent.persona.constants.temperaments import TEMPERAMENTS, Temperament
from agent.pg.models import Conversation
from agent.repositories.persona import PersonaRepository

_DISTRESS_MODES = frozenset({"listen", "ground", "safety"})
_DIAL_NAMES = tuple(f.name for f in fields(Dials))


@dataclass(frozen=True)
class PersonaState:
    user_id: str
    temperament: Temperament
    dials: Dials
    stage: int
    dependency_level: int
    traits: tuple[str, ...]
    trait_pending_reaction: bool
    recent_turns: tuple[Mapping[str, Any], ...]
    playful_last_four_turns: int
    distress_last_two_turns: bool
    locale: str = "en-US"
    timezone: str = "UTC"


def _resolve_dials(temperament: Temperament, *layers: Mapping[str, Any]) -> Dials:
    values = {name: getattr(temperament.default_dials, name) for name in _DIAL_NAMES}
    for layer in layers:
        for name in _DIAL_NAMES:
            v = (layer or {}).get(name)
            if isinstance(v, int) and not isinstance(v, bool):
                values[name] = v
    dials, _ = narrow_rejected_combinations(clamp_dials(Dials(**values)))
    return dials


async def load_persona_state(
    *,
    repo: PersonaRepository,
    user_id: str,
    recent_conversations: Sequence[Conversation],
    locale: str = "en-US",
    timezone: str = "UTC",
) -> PersonaState:
    persona = await repo.get_or_create(user_id, locale=locale, timezone=timezone)
    temperament = TEMPERAMENTS.get(persona.temperament, TEMPERAMENTS["steady"])
    dials = _resolve_dials(temperament, persona.dials, persona.learned_dials)

    traits = await repo.list_traits(user_id)
    active = tuple(t.label for t in traits if t.status == "active")
    pending = any(t.status == "trial" for t in traits)

    last_four = list(recent_conversations)[-4:]
    recent = tuple(
        {"asked_question": bool(c.asked_question), "mode": c.mode or "everyday"}
        for c in last_four
    )
    playful = sum(1 for c in last_four if c.mode == "banter")
    distress = any(
        (c.mode in _DISTRESS_MODES) or (c.concern_tier in ("concern", "acute"))
        for c in last_four[-2:]
    )
    return PersonaState(
        user_id=user_id,
        temperament=temperament,
        dials=dials,
        stage=persona.stage,
        dependency_level=persona.dependency_level,
        traits=active,
        trait_pending_reaction=pending,
        recent_turns=recent,
        playful_last_four_turns=playful,
        distress_last_two_turns=distress,
        locale=persona.locale,
        timezone=persona.timezone,
    )
