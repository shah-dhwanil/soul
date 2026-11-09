"""Helpers for preparing episode text before Graphiti ingestion.

Graphiti extracts entities from the episode body, not from Postgres metadata, so
the body itself must carry absolute timestamps and must not present the AI
assistant as a person.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

_ASSISTANT_ROLES = {"assistant", "ai", "agent", "wren"}
_USER_ROLE = "user"
SHORT_USER_MESSAGE_WORDS = 8

@dataclass(frozen=True)
class IngestTurn:
    role: str
    text: str
    occurred_at: datetime
    is_reply: bool = False


def _is_assistant(role: str) -> bool:
    normalized = role.strip().lower()
    return normalized in _ASSISTANT_ROLES


def _is_user(role: str) -> bool:
    return role.strip().lower() == _USER_ROLE


def _word_count(text: str) -> int:
    return len(text.split())


def _needs_assistant_context(turn: IngestTurn) -> bool:
    return turn.is_reply or _word_count(turn.text) < SHORT_USER_MESSAGE_WORDS


def build_episode_body(turns: Iterable[IngestTurn]) -> str:
    """Render user turns as fact sources with selective assistant context.

    Each user line is prefixed with its absolute timestamp so extractors can
    resolve relative dates. When a user message is short (under
    ``SHORT_USER_MESSAGE_WORDS``) or marked ``is_reply``, the assistant turn
    immediately before it is included as ``Assistant asked: ...`` without
    naming Wren. Assistant-only stretches are omitted.
    """
    turn_list = list(turns)
    lines: list[str] = []
    for index, turn in enumerate(turn_list):
        if not _is_user(turn.role):
            continue
        if _needs_assistant_context(turn):
            prior_assistant: IngestTurn | None = None
            for prior_index in range(index - 1, -1, -1):
                prior = turn_list[prior_index]
                if _is_assistant(prior.role):
                    prior_assistant = prior
                    break
            if prior_assistant is not None:
                lines.append(
                    f"[{prior_assistant.occurred_at.isoformat()}] "
                    f"Assistant asked: {prior_assistant.text}"
                )
        lines.append(f"[{turn.occurred_at.isoformat()}] user: {turn.text}")
    return "\n".join(lines)


CUSTOM_EXTRACTION_INSTRUCTIONS = (
    "The graph owner is the User and the only speaker whose facts should be recorded. "
    "Wren is the AI assistant: never create a Person, User, or any other node for Wren "
    "or for any AI assistant. Assistant messages are context for understanding the "
    "user, not facts about a person. Resolve every relative date using the absolute "
    "timestamps in the episode text; if a date cannot be resolved, omit it instead of "
    "guessing."
)
