from agent.persona.constants.dials import Dials
from agent.persona.constants.modes import Mode
from agent.persona.constants.temperaments import TEMPERAMENTS
from agent.persona.context import WrenPromptContext
from agent.persona.directive import TurnDirective
from agent.persona.render import render_wren_system_prompt


def _ctx(**overrides) -> WrenPromptContext:
    base = {
        "temperament": "a temperament",
        "dials": "some dials",
        "stage_permissions": "some permissions",
        "active_traits": "no shared language yet",
        "mode_block": "Listen: stay with it.",
        "turn_directive": "some directive",
        "banned_phrases": "some banned phrases",
        "configured_resources": "some resources",
        "memory_context": "(none)",
    }
    base.update(overrides)
    return WrenPromptContext(**base)


def test_render_replaces_all_placeholders():
    out = render_wren_system_prompt(_ctx())
    assert "{{" not in out
    assert "You are Wren" in out


def test_memory_context_never_appears_in_the_system_prompt():
    out = render_wren_system_prompt(_ctx(memory_context="secret-fact"))
    assert "secret-fact" not in out


def test_directive_appears_in_the_system_prompt():
    out = render_wren_system_prompt(_ctx(turn_directive="some directive"))
    assert "some directive" in out


def test_mode_block_appears_in_the_system_prompt():
    out = render_wren_system_prompt(_ctx(mode_block="Listen: stay with it."))
    assert "Listen: stay with it." in out


def test_prompt_context_from_turn_builds_layers():
    from agent.persona.context import prompt_context_from_turn

    directive = TurnDirective(
        mode=Mode.LISTEN,
        length_band=(8, 25),
        max_bubbles=3,
        question_allowed=True,
        advice_allowed=False,
        humor_allowed=False,
        callback_allowed=True,
        trait_allowed=False,
        concern_tier="normal",
        dependency_level=0,
        stage=1,
        closing_signal=False,
        reason_codes=(),
    )
    ctx = prompt_context_from_turn(
        decisions={"raw": {"answers": {}}},
        memories=[{"fact": "User likes chai"}],
        directive=directive,
        persona_state={
            "temperament": TEMPERAMENTS["steady"],
            "dials": Dials(formality=2, warmth=7, directness=6, humor=4, initiative=3),
            "stage": 1,
            "traits": [],
        },
    )
    assert "chai" in ctx.memory_context
    assert ctx.stage_permissions
    assert ctx.mode_block
    assert ctx.turn_directive
