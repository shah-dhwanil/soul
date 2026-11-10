"""Parse and prompt for Graphiti memory search query extraction."""

import json
import re

MEMORY_QUERY_SYSTEM = """\
You extract search queries for a personal knowledge graph about one user.
Reply with JSON only: a string array with 0 to 3 items.

Return [] when:
- the message is greeting, banter, or filler with nothing to look up
- there is no named person, event, date, place, preference, goal, or ongoing situation
- the user is not asking about something that might be stored as a fact

Return 1–3 short queries only when chat references concrete things worth retrieving
(names, relationships, plans, exams, jobs, pets, likes/dislikes, what happened).

Rules:
- Do not invent names or facts not in the message or recent chat.
- Do not output dictionary or translation queries for slang or casual phrases.
- Do not echo the whole message as a query unless it contains a retrievable entity.
"""


def build_memory_query_user_prompt(
    current_chat: str, history_text: str
) -> str:
    if history_text.strip():
        return (
            f"Recent chat:\n{history_text}\n\n"
            f"Current user message:\n{current_chat}"
        )
    return f"Current user message:\n{current_chat}"


def parse_memory_query_response(content: str) -> list[str]:
    """Parse model output; empty list on failure or explicit []."""
    stripped = content.strip()
    match = re.search(r"\[[\s\S]*\]", stripped)
    if not match:
        return []
    try:
        parsed = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(q).strip() for q in parsed[:3] if q and str(q).strip()]
