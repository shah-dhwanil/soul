from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    thread_id: UUID
    turn_id: UUID
    conversation_id: UUID | None
    reply: str
    new_thread: bool
    memory_degraded: bool
    decisions: dict[str, Any]
