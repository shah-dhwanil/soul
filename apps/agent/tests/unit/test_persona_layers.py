import re

from agent.persona.constants.dials import Dials
from agent.persona.constants.temperaments import TEMPERAMENTS
from agent.persona.layers import (
    render_active_traits,
    render_dials,
    render_stage_permissions,
    render_temperament,
)


def test_temperament_renderer_never_names_the_seed():
    out = render_temperament(TEMPERAMENTS["wry"])
    assert out
    assert "wry" not in out.lower()


def test_dials_renderer_contains_no_digits():
    out = render_dials(Dials(formality=2, warmth=6, directness=6, humor=5, initiative=3))
    assert out
    assert not re.search(r"\d", out)


def test_dials_renderer_states_a_reason():
    out = render_dials(Dials(formality=2, warmth=6, directness=6, humor=5, initiative=3))
    assert "warm" in out.lower()
    assert "disagree" in out.lower()


def test_stage_permissions_never_name_the_stage():
    for stage in (1, 2, 3):
        out = render_stage_permissions(stage).lower()
        assert "stage" not in out
        assert not re.search(r"\d", out)


def test_stage_one_hedges_interpretation():
    out = render_stage_permissions(1).lower()
    assert "might be reading" in out or "could be reading" in out


def test_stage_two_is_direct_about_named_patterns():
    out = render_stage_permissions(2).lower()
    assert "named" in out


def test_active_traits_renderer_handles_empty():
    assert render_active_traits([])


def test_active_traits_renderer_lists_phrases():
    out = render_active_traits(["the 3pm gallows", "Sunday dread"])
    assert "3pm gallows" in out
    assert "Sunday dread" in out
