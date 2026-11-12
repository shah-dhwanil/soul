"""Dial floors, ceilings, clamping, and rejected-combination narrowing (spec §5, §7)."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Dials:
    formality: int
    warmth: int
    directness: int
    humor: int
    initiative: int


DIAL_FLOORS = Dials(formality=1, warmth=5, directness=4, humor=0, initiative=2)
DIAL_CEILINGS = Dials(formality=4, warmth=8, directness=8, humor=6, initiative=5)


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def clamp_dials(dials: Dials) -> Dials:
    return Dials(
        formality=_clamp(dials.formality, DIAL_FLOORS.formality, DIAL_CEILINGS.formality),
        warmth=_clamp(dials.warmth, DIAL_FLOORS.warmth, DIAL_CEILINGS.warmth),
        directness=_clamp(dials.directness, DIAL_FLOORS.directness, DIAL_CEILINGS.directness),
        humor=_clamp(dials.humor, DIAL_FLOORS.humor, DIAL_CEILINGS.humor),
        initiative=_clamp(dials.initiative, DIAL_FLOORS.initiative, DIAL_CEILINGS.initiative),
    )


def narrow_rejected_combinations(dials: Dials) -> tuple[Dials, tuple[str, ...]]:
    """Narrow combinations the product rejects; one reason per adjustment."""
    reasons: list[str] = []
    adjusted = dials
    if adjusted.humor >= 5 and adjusted.warmth <= 5:
        adjusted = replace(adjusted, humor=min(adjusted.humor, adjusted.warmth))
        reasons.append("high humor with low warmth: humor lowered to match warmth")
    if adjusted.directness >= 7 and adjusted.warmth <= 5:
        adjusted = replace(adjusted, directness=6)
        reasons.append("high directness with low warmth: directness lowered to 6")
    return adjusted, tuple(reasons)
