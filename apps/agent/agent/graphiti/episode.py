"""Helpers for preparing episode text before Graphiti ingestion.

Graphiti extracts entities from the episode body, not from Postgres metadata, so
the body itself must carry absolute timestamps and must not present the AI
assistant as a person.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

_ASSISTANT_ROLES = {"assistant", "ai", "agent", "wren"}
_USER_ROLE = "user"
SHORT_USER_MESSAGE_WORDS = 8

_RELATIVE_WEEKDAY = re.compile(
    r"\b(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)

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


def resolve_next_monday(anchor: datetime) -> date:
    """First Monday strictly after anchor's calendar day (UTC)."""
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=UTC)
    d = anchor.date()
    days_ahead = (7 - d.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return d + timedelta(days=days_ahead)


def calendar_hint_line(anchor: datetime) -> str:
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=UTC)
    d = anchor.date()
    next_mon = resolve_next_monday(anchor)
    return (
        f"[{anchor.isoformat()}] REFERENCE_CALENDAR (UTC): anchor {d.isoformat()} "
        f"is {d.strftime('%A')}. For this message, 'next Monday' means "
        f"{next_mon.isoformat()}."
    )


def enrich_episode_body_with_calendar(
    body: str,
    *,
    user_messages: Iterable[tuple[datetime, str]],
) -> str:
    """Prepend deterministic weekday resolution when user text uses relative days."""
    if not _RELATIVE_WEEKDAY.search(body):
        return body
    hints: list[str] = []
    seen: set[str] = set()
    for started_at, text in user_messages:
        if not _RELATIVE_WEEKDAY.search(text):
            continue
        key = started_at.isoformat()
        if key in seen:
            continue
        seen.add(key)
        hints.append(calendar_hint_line(started_at))
    if not hints:
        return body
    return "\n".join(hints) + "\n" + body


CUSTOM_EXTRACTION_INSTRUCTIONS = (
    "The graph owner is the User and the only speaker whose facts should be recorded. "
    "Wren is the AI assistant: never create a Person, User, or any other node for Wren "
    "or for any AI assistant. Assistant messages are context for understanding the "
    "user, not facts about a person. Resolve every relative date using REFERENCE_CALENDAR "
    "lines and bracketed timestamps in the episode text; if a date cannot be resolved, "
    "omit it instead of guessing."
)
