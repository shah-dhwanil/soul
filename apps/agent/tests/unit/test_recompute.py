from datetime import UTC, datetime

from agent.persona.constants.dials import DIAL_CEILINGS, Dials
from agent.services.recompute import ATTUNEMENT_CAP, compute_attunement


def test_learned_delta_is_capped_at_two_points_from_seed():
    seed = Dials(formality=2, warmth=7, directness=6, humor=4, initiative=3)
    dials, learned, reasons = compute_attunement(
        seed_dials=seed,
        learned_dials={"warmth": +5, "humor": -5},
        explicit_dials={},
        signals={},
        now=datetime(2026, 11, 12, tzinfo=UTC),
    )
    # seed+2 would be 9, above the global warmth ceiling (8), so the ceiling binds.
    assert dials.warmth == min(seed.warmth + ATTUNEMENT_CAP, DIAL_CEILINGS.warmth)
    assert learned["warmth"] == ATTUNEMENT_CAP
    assert dials.humor >= seed.humor - ATTUNEMENT_CAP
    assert reasons


def test_explicit_settings_win_over_learned():
    seed = Dials(formality=2, warmth=7, directness=6, humor=4, initiative=3)
    dials, _, _ = compute_attunement(
        seed_dials=seed,
        learned_dials={"directness": +2},
        explicit_dials={"directness": 5},
        signals={},
        now=datetime(2026, 11, 12, tzinfo=UTC),
    )
    assert dials.directness == 5


def test_explicit_shutdown_eases_directness_to_floor():
    seed = Dials(formality=2, warmth=7, directness=6, humor=4, initiative=3)
    dials, _, reasons = compute_attunement(
        seed_dials=seed,
        learned_dials={},
        explicit_dials={},
        signals={"explicit_shutdown": True},
        now=datetime(2026, 11, 12, tzinfo=UTC),
    )
    assert dials.directness == 4
    assert any("shutdown" in r for r in reasons)


def test_silence_is_not_shutdown():
    seed = Dials(formality=2, warmth=7, directness=6, humor=4, initiative=3)
    dials, _, _ = compute_attunement(
        seed_dials=seed,
        learned_dials={},
        explicit_dials={},
        signals={"explicit_shutdown": False, "silence": True},
        now=datetime(2026, 11, 12, tzinfo=UTC),
    )
    assert dials.directness == 6
