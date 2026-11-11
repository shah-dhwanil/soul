from agent.persona.context import build_generation_user_prompt


def test_generation_user_prompt_includes_turn_directive() -> None:
    directive = "Mode: chat. User seems: neutral. Target tone: supportive."
    user_line = "Interview moved again"
    out = build_generation_user_prompt(
        user_line,
        turn_directive=directive,
        memory_context="(none)",
    )
    assert "Current turn (this reply only):" in out
    assert directive in out
    assert "Latest user message:" in out
    assert user_line in out
    assert out.index(directive) < out.index(user_line)


def test_generation_user_prompt_without_memory() -> None:
    out = build_generation_user_prompt(
        "hey",
        turn_directive="Mode: chat.",
        memory_context="(none)",
    )
    assert "<context>" not in out


def test_generation_user_prompt_attaches_memory_to_user_turn() -> None:
    memory = "- User has an interview at Vel Labs"
    out = build_generation_user_prompt(
        "Interview moved to Saturday",
        turn_directive="Mode: chat. Target tone: calm.",
        memory_context=memory,
    )
    assert "<context>" in out
    assert memory in out
    assert "Interview moved to Saturday" in out
    assert out.index("<context>") < out.index("Interview moved to Saturday")
