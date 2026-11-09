"""Chat turn shapes passed through the graph."""

from dataclasses import dataclass

from agent.pg.models import Conversation


@dataclass(frozen=True)
class ChatTurn:
    user_message: str
    agent_response: str

    @classmethod
    def from_conversation(cls, row: Conversation) -> "ChatTurn":
        return cls(
            user_message=row.user_message,
            agent_response=row.agent_response,
        )


def format_turns_for_clef(turns: list[ChatTurn], current_message: str) -> str:
    lines: list[str] = []
    for turn in turns:
        lines.append(f"user: {turn.user_message}")
        lines.append(f"assistant: {turn.agent_response}")
    lines.append(f"user: {current_message}")
    return "\n".join(lines)


def turns_to_langchain_pairs(turns: list[ChatTurn]) -> list[tuple[str, str]]:
    return [(t.user_message, t.agent_response) for t in turns]
