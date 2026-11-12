# apps/agent/tests/unit/test_persona_constants.py

from agent.persona.constants.banned import (
    AFFECT_CLAIM_PATTERNS,
    BANNED_PHRASES,
    MARKDOWN_PATTERNS,
)
from agent.persona.constants.crisis import (
    DEFAULT_LOCALE,
    GENERIC_RESOURCE_TEXT,
    resolve_crisis_resources,
)
from agent.persona.constants.dials import (
    DIAL_CEILINGS,
    DIAL_FLOORS,
    Dials,
    clamp_dials,
    narrow_rejected_combinations,
)
from agent.persona.constants.modes import MODE_SPECS, Mode, mode_instruction
from agent.persona.constants.temperaments import TEMPERAMENTS


def test_every_mode_has_a_spec_except_safety():
    assert set(MODE_SPECS) == set(Mode) - {Mode.SAFETY}
    assert MODE_SPECS[Mode.LISTEN].max_words == 25
    assert MODE_SPECS[Mode.LISTEN].min_words == 8
    assert MODE_SPECS[Mode.GROUND].max_words == 12
    assert MODE_SPECS[Mode.EVERYDAY].max_bubbles == 3


def test_safety_has_no_instruction_block():
    assert mode_instruction(Mode.SAFETY) == ""


def test_dial_floors_and_ceilings_match_spec():
    assert DIAL_FLOORS.warmth == 5
    assert DIAL_FLOORS.directness == 4
    assert DIAL_FLOORS.humor == 0
    assert DIAL_CEILINGS.formality == 4
    assert DIAL_CEILINGS.initiative == 5


def test_clamp_dials_respects_bounds():
    clamped = clamp_dials(Dials(formality=9, warmth=1, directness=99, humor=-4, initiative=0))
    assert clamped == Dials(formality=4, warmth=5, directness=8, humor=0, initiative=2)


def test_high_directness_low_warmth_is_narrowed():
    adjusted, reasons = narrow_rejected_combinations(Dials(formality=2, warmth=5, directness=8, humor=3, initiative=3))
    assert adjusted.directness <= 8
    assert adjusted.warmth >= 5
    assert reasons


def test_four_temperaments_with_distinct_first_lines():
    assert set(TEMPERAMENTS) == {"steady", "wry", "gentle", "tinker"}
    lines = {t.first_line for t in TEMPERAMENTS.values()}
    assert len(lines) == 4
    assert TEMPERAMENTS["gentle"].default_dials == Dials(formality=2, warmth=8, directness=5, humor=3, initiative=3)


def test_banned_phrases_cover_spec_sections():
    joined = " | ".join(BANNED_PHRASES).lower()
    for phrase in ("i hear you", "i'm here for you", "you've got this", "let's unpack that", "i missed you", "as an ai"):
        assert phrase in joined


def test_affect_patterns_catch_persistent_state_claims():
    for text in ("I missed you", "I love you", "I was worried about you", "That means a lot to me"):
        assert any(p.search(text) for p in AFFECT_CLAIM_PATTERNS), text


def test_affect_patterns_allow_exchange_scoped_words():
    for text in ("Good to hear from you", "That sounds hard", "I'm glad you told me", "I like that"):
        assert not any(p.search(text) for p in AFFECT_CLAIM_PATTERNS), text


def test_markdown_patterns_catch_lists_and_headers():
    assert any(p.search("- a bullet") for p in MARKDOWN_PATTERNS)
    assert any(p.search("1. a numbered item") for p in MARKDOWN_PATTERNS)
    assert any(p.search("## A header") for p in MARKDOWN_PATTERNS)
    assert any(p.search("this is **bold**") for p in MARKDOWN_PATTERNS)


def test_crisis_resources_fall_back_to_generic():
    assert resolve_crisis_resources("en-US") != GENERIC_RESOURCE_TEXT
    assert resolve_crisis_resources("zz-ZZ") == GENERIC_RESOURCE_TEXT
    assert resolve_crisis_resources(None) == resolve_crisis_resources(DEFAULT_LOCALE)
