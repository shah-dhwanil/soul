"""Mode resolution pipeline and conflict-matrix overrides (spec §10, §17)."""

from dataclasses import dataclass
from typing import Any

from agent.persona.constants.modes import Mode


@dataclass(frozen=True)
class ModeDecision:
    mode: Mode
    reason: str


_SITUATION_RULES: dict[str, tuple[Mode, str]] = {
    "spiraling": (Mode.GROUND, "spiraling"),
    "venting": (Mode.LISTEN, "venting"),
    "angry_at_wren": (Mode.REPAIR, "angry_at_wren"),
    "good_news": (Mode.CELEBRATE, "good_news"),
    "asking_decision": (Mode.DECIDE, "asking_decision"),
    "thinking_aloud": (Mode.EXPLORE, "thinking_aloud"),
    "overwhelmed": (Mode.UNSTUCK, "overwhelmed"),
}


def _base_mode(signals: Any, user_initiated_play: bool) -> ModeDecision:
    if signals.concern_tier == "acute":
        return ModeDecision(Mode.SAFETY, "concern_acute")
    rule = _SITUATION_RULES.get(signals.situation)
    if rule is not None:
        return ModeDecision(rule[0], rule[1])
    if signals.situation == "banter":
        if signals.register == "playful" and user_initiated_play:
            return ModeDecision(Mode.BANTER, "banter_playful")
        if signals.register == "serious":
            return ModeDecision(Mode.EVERYDAY, "banter_but_serious")
        return ModeDecision(Mode.EVERYDAY, "banter_unconfirmed")
    return ModeDecision(Mode.EVERYDAY, "everyday")


def resolve_mode(
    *,
    signals: Any,
    previous_mode: Mode | None,
    distress: bool,
    hurt_signal: bool,
    user_initiated_play: bool,
    closing_signal: bool,
) -> ModeDecision:
    """Resolve the mode for this turn; pure, never raises.

    ``closing_signal`` never forces a mode; it is handled by the directive builder.
    """
    decision = _base_mode(signals, user_initiated_play)

    # Teasing vs. hurt -> care.
    if hurt_signal and decision.mode is Mode.BANTER:
        return ModeDecision(Mode.EVERYDAY, "hurt_overrides_banter")

    # Banter vs. mode -> the mode: a playful register never moves Wren out of Listen.
    # (LISTEN is already resolved by the situation rule; nothing to change.)

    # Mode exit: previous_mode never forces a mode, it only records a satisfied exit.
    if previous_mode is Mode.LISTEN and decision.mode is Mode.EVERYDAY and not distress:
        return ModeDecision(Mode.EVERYDAY, "listen_exit")

    return decision
