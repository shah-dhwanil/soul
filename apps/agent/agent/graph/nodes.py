from typing import Literal
from uuid import UUID

from langchain_core.runnables import RunnableConfig

from agent.graph.deps import GraphDeps, deps_from_config
from agent.graph.state import TurnState
from agent.history import ChatTurn


async def classify_parallel(state: TurnState, config: RunnableConfig) -> TurnState:
    deps = deps_from_config(config)
    decisions = await deps.decision_model.get_decisions(
        state["user_message"],
        state.get("decision_history") or [],
    )
    return TurnState(
        decisions=decisions,
        inject_previous_chat=decisions["inject_previous_chat"],
        split_thread=decisions["split_thread"],
        memory_required=decisions["memory_required"],
    )


async def apply_thread_policy(state: TurnState, config: RunnableConfig) -> TurnState:
    deps = deps_from_config(config)
    db_thread_id = UUID(state["db_thread_id"])
    settings = deps.settings
    repo = deps.get_conversation_repo()

    pipeline: list[ChatTurn] = []
    generation: list[ChatTurn] = []
    previous_id: str | None = None
    ingest_pending: str | None = None
    new_thread = False
    updated_db_thread = state["db_thread_id"]

    if state.get("split_thread"):
        rows = await repo.list_by_thread(
            db_thread_id, limit=settings.split_generation_history_limit
        )
        generation = [ChatTurn.from_conversation(r) for r in rows]
        if rows:
            previous_id = state["db_thread_id"]
            new_id = await deps.get_thread_service().rotate(state["user_id"], db_thread_id)
            updated_db_thread = str(new_id)
            ingest_pending = previous_id
            new_thread = True
        pipeline = []
    elif state.get("inject_previous_chat"):
        rows = await repo.list_recent_for_thread(
            db_thread_id, settings.pipeline_history_limit
        )
        pipeline = [ChatTurn.from_conversation(r) for r in rows]
        generation = pipeline

    return TurnState(
        db_thread_id=updated_db_thread,
        previous_db_thread_id=previous_id,
        pipeline_history=pipeline,
        generation_history=generation,
        ingest_pending_thread_id=ingest_pending,
        new_thread_created=new_thread,
    )


async def plan_memory(state: TurnState, config: RunnableConfig) -> TurnState:
    if not state.get("memory_required"):
        return TurnState(memory_queries=[])
    deps = deps_from_config(config)
    queries = await deps.query_llm.get_queries(
        state["user_message"],
        state.get("pipeline_history") or [],
    )
    if state["user_message"] and state["user_message"] not in queries:
        queries.append(state["user_message"][:200])
    return TurnState(memory_queries=queries)


def route_memory(state: TurnState) -> Literal["retrieve_memory", "assemble_and_generate"]:
    if state.get("memory_required"):
        return "retrieve_memory"
    return "assemble_and_generate"


async def retrieve_memory(state: TurnState, config: RunnableConfig) -> TurnState:
    deps = deps_from_config(config)
    queries = state.get("memory_queries") or []
    memories, degraded = await deps.memory_service.search(state["user_id"], queries)
    return TurnState(memories=memories, memory_degraded=degraded)


async def assemble_and_generate(state: TurnState, config: RunnableConfig) -> TurnState:
    deps = deps_from_config(config)
    raw = (state.get("decisions") or {}).get("raw") or {}
    answers = raw.get("answers") or {}
    agent_emotion = answers.get("agent_emotion", {})
    tone_hint = None
    if isinstance(agent_emotion, dict) and agent_emotion.get("label"):
        tone_hint = str(agent_emotion["label"])

    reply = await deps.query_llm.generate_response(
        state["user_message"],
        state.get("generation_history") or [],
        state.get("memories") or [],
        tone_hint=tone_hint,
    )
    return TurnState(
        reply=reply,
        prompt_meta={"model": deps.settings.groq_agent_model},
    )


async def persist_turn(state: TurnState, config: RunnableConfig) -> TurnState:
    final_state = {
        "decisions": state.get("decisions"),
        "memory_degraded": state.get("memory_degraded", False),
        "split_thread": state.get("split_thread", False),
        "new_thread_created": state.get("new_thread_created", False),
        "previous_db_thread_id": state.get("previous_db_thread_id"),
        "ingest_pending": state.get("ingest_pending_thread_id"),
        "turn_id": state.get("turn_id"),
    }
    return TurnState(final_state=final_state)
