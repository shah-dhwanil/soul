"""Onboarding samples and the deterministic first-meeting line (spec §6, §19).

The first message is model-free: it is inserted, never generated.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from agent.persona.constants.temperaments import (
    DEFAULT_TEMPERAMENT_ID,
    TEMPERAMENTS,
    Temperament,
)

_ONBOARDING_PAIR = ("steady", "wry")  # a real contrast: even and dry vs. quick and playful

_FIRST_MEETING_MOVES: tuple[str, ...] = (
    "Say one honest line about yourself, in your own voice: you are an AI, you remember, "
    "and you say what you actually think.",
    "Within the first few exchanges, offer a small point of view: a mild opinion about a "
    "situation or a thing they mention, never about their faults.",
    "Ask one specific question about something they said. Not a questionnaire.",
    "Offer a concrete reason to come back, lightly and never as pressure. It is an "
    "invitation, not a schedule: if they take it up they have opted in to a check-in about "
    "that one thing; if they do not, nothing is sent.",
    "Use your temperament's humor from turn one, aimed at situations, never at the user.",
)


@dataclass(frozen=True)
class OnboardingSample:
    temperament_id: str
    sample_reply: str


def _temperament(temperament_id: str) -> Temperament:
    return TEMPERAMENTS.get(temperament_id) or TEMPERAMENTS[DEFAULT_TEMPERAMENT_ID]


def onboarding_samples() -> tuple[OnboardingSample, ...]:
    return tuple(
        OnboardingSample(temperament_id=tid, sample_reply=TEMPERAMENTS[tid].sample_reply)
        for tid in _ONBOARDING_PAIR
    )


def first_line_for(temperament_id: str) -> str:
    """The §6 first line for the seed, verbatim; unknown seeds fall back to steady."""
    return _temperament(temperament_id).first_line


def first_meeting_moves(temperament_id: str) -> tuple[str, ...]:
    """The five §6 moves as prose guidance for the prompt. Nothing here is ever sent."""
    _temperament(temperament_id)
    return _FIRST_MEETING_MOVES


async def create_first_conversation(
    *, repo, user_id: str, temperament_id: str, thread_id: UUID
) -> str:
    """Insert the deterministic first line as the first assistant message."""
    line = first_line_for(temperament_id)
    await repo.create(
        thread_id=thread_id,
        user_message="",
        agent_response=line,
        final_state={
            "first_meeting": True,
            "temperament": _temperament(temperament_id).id,
            "user_id": user_id,
        },
    )
    return line
