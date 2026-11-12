import logging
from typing import Literal
from uuid import UUID

logger = logging.getLogger(__name__)

from langchain_core.runnables import RunnableConfig

from agent.graph.deps import deps_from_config
from agent.graph.state import TurnState
from agent.history import ChatTurn
from agent.persona.constants.dials import Dials
from agent.persona.constants.modes import Mode
from agent.persona.constants.temperaments import TEMPERAMENTS
from agent.persona.context import prompt_context_from_turn
from agent.persona.directive import TurnDirective

# Temporary stubs until Task 14 wires real directive/persona state into the graph.
_STUB_DIRECTIVE = TurnDirective(
    mode=Mode.EVERYDAY,
    length_band=(8, 25),
    max_bubbles=3,
    question_allowed=True,
    advice_allowed=False,
    humor_allowed=False,
    callback_allowed=True,
    trait_allowed=False,
    concern_tier="normal",
    dependency_level=0,
    stage=1,
    closing_signal=False,
    reason_codes=(),
)
_STUB_PERSONA_STATE = {
    "temperament": TEMPERAMENTS["steady"],
    "dials": Dials(formality=2, warmth=7, directness=6, humor=4, initiative=3),
    "stage": 1,
    "traits": [],
}


async def classify_parallel(state: TurnState, config: RunnableConfig) -> TurnState:
    deps = deps_from_config(config)
    decisions = await deps.decision_model.get_decisions(
        state["user_message"],
        state.get("decision_history") or [],
    )
    out = TurnState(
        decisions=decisions,
        inject_previous_chat=decisions["inject_previous_chat"],
        split_thread=decisions["split_thread"],
        memory_required=decisions["memory_required"],
    )
    logger.info(
        "classify turn=%s inject=%s split=%s memory=%s",
        state.get("turn_id"),
        out["inject_previous_chat"],
        out["split_thread"],
        out["memory_required"],
    )
    return out


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

    split_requested = bool(state.get("split_thread"))
    rows_for_split: list = []
    if split_requested:
        rows_for_split = await repo.list_by_thread(
            db_thread_id, limit=settings.split_generation_history_limit
        )

    split_thread = (
        split_requested
        and len(rows_for_split) >= settings.min_turns_before_split
    )
    if split_requested and not split_thread:
        logger.info(
            "thread_policy suppressed split turn=%s turns_in_thread=%d min=%d",
            state.get("turn_id"),
            len(rows_for_split),
            settings.min_turns_before_split,
        )

    if split_thread:
        generation = [ChatTurn.from_conversation(r) for r in rows_for_split]
        if rows_for_split:
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

    out = TurnState(
        db_thread_id=updated_db_thread,
        previous_db_thread_id=previous_id,
        pipeline_history=pipeline,
        generation_history=generation,
        ingest_pending_thread_id=ingest_pending,
        new_thread_created=new_thread,
    )
    logger.info(
        "thread_policy turn=%s new_thread=%s pipeline_turns=%d generation_turns=%d",
        state.get("turn_id"),
        new_thread,
        len(pipeline),
        len(generation),
    )
    return out


async def plan_memory(state: TurnState, config: RunnableConfig) -> TurnState:
    deps = deps_from_config(config)
    queries = await deps.query_llm.get_queries(
        state["user_message"],
        state.get("pipeline_history") or [],
    )
    logger.info(
        "plan_memory turn=%s clef_memory=%s queries=%s",
        state.get("turn_id"),
        state.get("memory_required"),
        queries,
    )
    return TurnState(memory_queries=queries)


def route_memory(state: TurnState) -> Literal["retrieve_memory", "assemble_and_generate"]:
    if state.get("memory_queries") or []:
        return "retrieve_memory"
    return "assemble_and_generate"


async def retrieve_memory(state: TurnState, config: RunnableConfig) -> TurnState:
    deps = deps_from_config(config)
    queries = state.get("memory_queries") or []
    memories, degraded = await deps.memory_service.search(state["user_id"], queries)
    return TurnState(memories=memories, memory_degraded=degraded)


async def assemble_and_generate(state: TurnState, config: RunnableConfig) -> TurnState:
    deps = deps_from_config(config)
    crisis = deps.settings.crisis_resources or None
    persona = prompt_context_from_turn(
        decisions=state.get("decisions"),
        memories=state.get("memories") or [],
        configured_resources=crisis,
        # TODO(Task 14): replace stub directive/persona_state with real values.
        directive=_STUB_DIRECTIVE,
        persona_state=_STUB_PERSONA_STATE,
    )
    reply = await deps.query_llm.generate_response(
        state["user_message"],
        state.get("generation_history") or [],
        persona=persona,
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
