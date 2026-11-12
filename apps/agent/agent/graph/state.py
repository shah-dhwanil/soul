from typing import Any, TypedDict
from uuid import UUID

from agent.history import ChatTurn
from agent.persona.directive import TurnDirective
from agent.services.persona_state import PersonaState


class TurnState(TypedDict, total=False):
    user_id: str
    turn_id: str
    db_thread_id: str
    previous_db_thread_id: str | None
    user_message: str
    decision_history: list[ChatTurn]
    pipeline_history: list[ChatTurn]
    generation_history: list[ChatTurn]
    decisions: dict[str, Any]
    inject_previous_chat: bool
    split_thread: bool
    memory_required: bool
    memory_queries: list[str]
    memories: list[dict[str, Any]]
    memory_degraded: bool
    reply: str
    prompt_meta: dict[str, Any]
    final_state: dict[str, Any]
    ingest_pending_thread_id: str | None
    new_thread_created: bool
    concern_tier: str
    register: str
    situation: str
    mode: str
    directive: TurnDirective | None
    persona_state: PersonaState | None
    validation: dict[str, Any]
    reply_source: str  # "model", "safety", "concern", "boundary"
    reply_is_safety: bool
    concern_asked_this_episode: bool



def initial_state(
    *,
    user_id: str,
    turn_id: UUID,
    db_thread_id: UUID,
    user_message: str,
    decision_history: list[ChatTurn],
) -> TurnState:
    return TurnState(
        user_id=user_id,
        turn_id=str(turn_id),
        db_thread_id=str(db_thread_id),
        previous_db_thread_id=None,
        user_message=user_message,
        decision_history=decision_history,
        pipeline_history=[],
        generation_history=[],
        decisions={},
        inject_previous_chat=False,
        split_thread=False,
        memory_required=False,
        memory_queries=[],
        memories=[],
        memory_degraded=False,
        reply="",
        prompt_meta={},
        final_state={},
        ingest_pending_thread_id=None,
        new_thread_created=False,
        concern_tier="normal",
        register="",
        situation="",
        mode="",
        directive=None,
        persona_state=None,
        validation={},
        reply_source="",
        reply_is_safety=False,
        concern_asked_this_episode=False,
    )
