"""Structured per-turn directive and its prose rendering."""

from dataclasses import dataclass

from agent.persona.constants.modes import Mode, mode_instruction


@dataclass(frozen=True)
class TurnDirective:
    mode: Mode
    length_band: tuple[int, int]
    max_bubbles: int
    question_allowed: bool
    advice_allowed: bool
    humor_allowed: bool
    callback_allowed: bool
    trait_allowed: bool
    concern_tier: str
    dependency_level: int
    stage: int
    closing_signal: bool
    reason_codes: tuple[str, ...]


def _length_phrase(band: tuple[int, int]) -> str:
    high = band[1]
    if high <= 12:
        return "Keep it to a few words per message."
    if high <= 20:
        return "Keep each message to a short line."
    return "Keep each message to a sentence or two."


def _bubble_phrase(count: int) -> str:
    if count <= 1:
        return "Send a single message."
    if count == 2:
        return "Send two messages at most."
    return "Send a few short messages at most."


def render_directive(directive: TurnDirective) -> str:
    moment = directive.mode.value.replace("_", " ")
    lines = [
        f"This turn is a {moment} moment.",
        mode_instruction(directive.mode),
        _length_phrase(directive.length_band),
        _bubble_phrase(directive.max_bubbles),
        "You may ask one question."
        if directive.question_allowed
        else "Do not ask a question.",
        "Advice is welcome if it helps."
        if directive.advice_allowed
        else "Do not advise; no advice this turn.",
        "Humour is fine if it fits."
        if directive.humor_allowed
        else "Leave humour out this turn.",
        "You may call back to something they said earlier."
        if directive.callback_allowed
        else "Do not call back to earlier conversations.",
        "You may use shared language."
        if directive.trait_allowed
        else "Do not use shared language this turn.",
    ]
    if directive.closing_signal:
        lines.append("They sound ready to wrap up; let the conversation close gently.")
    return " ".join(line for line in lines if line)
