from agent.persona.context import WrenPromptContext, prompt_context_from_turn
from agent.persona.loader import load_persona
from agent.persona.render import render_wren_system_prompt


def test_render_replaces_all_placeholders() -> None:
    ctx = WrenPromptContext(
        temperament="t",
        dials="d",
        stage_permissions="s",
        active_traits="a",
        banned_phrases="b",
        configured_resources="r",
        turn_directive="Mode: chat. User seems: anxious.",
        memory_context="secret-fact",
    )
    out = render_wren_system_prompt(ctx)
    assert "{{" not in out
    assert "You are Wren" in out
    assert "secret-fact" not in out
    assert "anxious" not in out
    assert "Current turn" not in out
    assert out != load_persona().prompt


def test_prompt_context_from_turn_uses_memory_facts() -> None:
    ctx = prompt_context_from_turn(
        decisions={"raw": {"answers": {}}},
        memories=[{"fact": "User likes chai"}],
    )
    assert "chai" in ctx.memory_context
    assert "I hear you" in ctx.banned_phrases
