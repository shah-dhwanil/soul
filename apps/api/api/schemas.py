from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class ChatResponse(BaseModel):
    thread_id: UUID
    turn_id: UUID
    conversation_id: UUID | None
    reply: str
    new_thread: bool
    memory_degraded: bool
    decisions: dict[str, Any]
