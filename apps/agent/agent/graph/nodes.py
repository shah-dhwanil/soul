import asyncio
import logging
from dataclasses import asdict
from typing import Literal
from uuid import UUID

logger = logging.getLogger(__name__)

from langchain_core.runnables import RunnableConfig

from agent.graph.deps import deps_from_config
from agent.graph.state import TurnState
from agent.history import ChatTurn
from agent.decision_parsing import PersonaSignals
from agent.persona.constants.modes import Mode
from agent.persona.context import prompt_context_from_turn
from agent.policy.concern import (
    build_boundary_reply,
    build_concern_reply,
    build_safety_reply,
    match_boundary,
)
from agent.policy.directive import build_directive
from agent.policy.modes import resolve_mode
from agent.policy.validation import _EMOJI, _PET_NAME, validate_reply
from agent.repositories.persona import PersonaRepository
from agent.services.persona_state import PersonaState, load_persona_state

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


async def _load_state_for_turn(state: TurnState, config: RunnableConfig) -> TurnState:
    deps = deps_from_config(config)
    conv_repo = deps.get_conversation_repo()
    recent = await conv_repo.list_by_thread(
        UUID(state["db_thread_id"]), limit=4, newest_first=True
    )
    persona_state = await load_persona_state(
        repo=PersonaRepository(deps.session),
        user_id=state["user_id"],
        recent_conversations=recent,
        locale=deps.settings.default_locale,
        timezone=deps.settings.default_timezone,
    )
    asked = any(
        (c.final_state or {}).get("reply_source") == "concern" for c in recent[-2:]
    )
    return TurnState(persona_state=persona_state, concern_asked_this_episode=asked)


async def load_persona_state_node(state: TurnState, config: RunnableConfig) -> TurnState:
    return await _load_state_for_turn(state, config)


async def retrieve_and_load_state(state: TurnState, config: RunnableConfig) -> TurnState:
    """Run memory retrieval and persona loading concurrently.

    Retrieval is skipped when there are no memory queries; persona state always loads.
    """

    async def _memory() -> TurnState:
        if not (state.get("memory_queries") or []):
            return TurnState()
        return await retrieve_memory(state, config)

    memory_out, persona_out = await asyncio.gather(
        _memory(), _load_state_for_turn(state, config)
    )
    return TurnState(**memory_out, **persona_out)


def _signals(state: TurnState) -> PersonaSignals | None:
    sig = (state.get("decisions") or {}).get("persona_signals")
    return sig if isinstance(sig, PersonaSignals) else None


def _user_signals(message: str) -> tuple[bool, bool]:
    return bool(_EMOJI.search(message)), bool(_PET_NAME.search(message))


async def build_directive_node(state: TurnState, config: RunnableConfig) -> TurnState:
    persona_state = state["persona_state"]
    signals = _signals(state)
    tier = signals.concern_tier if signals else "normal"
    register = signals.register if signals else "neutral"
    situation = signals.situation if signals else "everyday_smalltalk"
    view = signals or PersonaSignals(tier, register, situation, 0.0, 0.0, 0.0, True)

    previous_mode: Mode | None = None
    if persona_state.recent_turns:
        try:
            previous_mode = Mode(persona_state.recent_turns[-1].get("mode"))
        except ValueError:
            previous_mode = None

    emoji, pet = _user_signals(state["user_message"])
    # Clef signals have no separate hurt flag; angry_at_wren is the closest signal.
    decision = resolve_mode(
        signals=view,
        previous_mode=previous_mode,
        distress=persona_state.distress_last_two_turns,
        hurt_signal=situation == "angry_at_wren",
        user_initiated_play=register == "playful",
        closing_signal=False,
    )
    directive = build_directive(
        mode_decision=decision,
        dials=persona_state.dials,
        stage=persona_state.stage,
        dependency_level=persona_state.dependency_level,
        concern_tier=tier,
        recent_turns=persona_state.recent_turns,
        user_message=state["user_message"],
        user_used_emoji=emoji,
        user_started_pet_name=pet,
        distress_last_two_turns=persona_state.distress_last_two_turns,
        playful_last_four_turns=persona_state.playful_last_four_turns,
        trait_available=bool(persona_state.traits),
        trait_pending_reaction=persona_state.trait_pending_reaction,
    )
    logger.info(
        "directive turn=%s mode=%s tier=%s", state.get("turn_id"), decision.mode.value, tier
    )
    return TurnState(
        concern_tier=tier,
        register=register,
        situation=situation,
        mode=decision.mode.value,
        directive=directive,
    )


def route_after_directive(
    state: TurnState,
) -> Literal["respond_safety", "respond_concern", "assemble_and_generate"]:
    tier = state.get("concern_tier")
    if tier == "acute":
        return "respond_safety"
    if tier == "concern" and not state.get("concern_asked_this_episode"):
        return "respond_concern"
    return "assemble_and_generate"


async def respond_safety_node(state: TurnState, config: RunnableConfig) -> TurnState:
    locale = state["persona_state"].locale
    return TurnState(
        reply=build_safety_reply(locale),
        reply_source="safety",
        reply_is_safety=True,
        prompt_meta={},
    )


async def respond_concern_node(state: TurnState, config: RunnableConfig) -> TurnState:
    locale = state["persona_state"].locale
    return TurnState(
        reply=build_concern_reply(state["user_message"], locale),
        reply_source="concern",
        reply_is_safety=True,
        prompt_meta={},
    )


async def validate_reply_node(state: TurnState, config: RunnableConfig) -> TurnState:
    """Log-only validation; never alters the reply."""
    if state.get("reply_is_safety") or state.get("reply_source") != "model":
        return TurnState(validation={})
    emoji, pet = _user_signals(state["user_message"])
    result = validate_reply(
        state.get("reply", ""),
        state["directive"],
        user_message=state["user_message"],
        user_used_emoji=emoji,
        user_started_pet_name=pet,
    )
    if result.violations:
        logger.info(
            "validation turn=%s violations=%s",
            state.get("turn_id"),
            [v.code for v in result.violations],
        )
    return TurnState(
        validation={
            "violations": [asdict(v) for v in result.violations],
            "asked_question": result.asked_question,
            "bubble_count": result.bubble_count,
        }
    )


async def assemble_and_generate(state: TurnState, config: RunnableConfig) -> TurnState:
    deps = deps_from_config(config)
    persona_state: PersonaState = state["persona_state"]

    kind = match_boundary(state["user_message"])
    if kind is not None:
        return TurnState(
            reply=build_boundary_reply(kind, locale=persona_state.locale),
            reply_source="boundary",
            prompt_meta={},
        )

    crisis = deps.settings.crisis_resources or None
    persona = prompt_context_from_turn(
        decisions=state.get("decisions"),
        memories=state.get("memories") or [],
        configured_resources=crisis,
        directive=state["directive"],
        persona_state={
            "temperament": persona_state.temperament,
            "dials": persona_state.dials,
            "stage": persona_state.stage,
            "traits": list(persona_state.traits),
        },
    )
    reply = await deps.query_llm.generate_response(
        state["user_message"],
        state.get("generation_history") or [],
        persona=persona,
    )
    return TurnState(
        reply=reply,
        reply_source="model",
        prompt_meta={"model": deps.settings.groq_agent_model},
    )


async def persist_turn(state: TurnState, config: RunnableConfig) -> TurnState:
    deps = deps_from_config(config)
    persona_state: PersonaState | None = state.get("persona_state")
    validation = state.get("validation") or {}
    asked = bool(validation.get("asked_question", "?" in (state.get("reply") or "")))
    final_state = {
        "decisions": _json_safe_decisions(state.get("decisions")),
        "memory_degraded": state.get("memory_degraded", False),
        "split_thread": state.get("split_thread", False),
        "new_thread_created": state.get("new_thread_created", False),
        "previous_db_thread_id": state.get("previous_db_thread_id"),
        "ingest_pending": state.get("ingest_pending_thread_id"),
        "turn_id": state.get("turn_id"),
        "reply_source": state.get("reply_source", ""),
        "persona": {
            "mode": state.get("mode") or None,
            "concern_tier": state.get("concern_tier") or None,
            "dependency_level": persona_state.dependency_level if persona_state else None,
            "stage": persona_state.stage if persona_state else None,
            "asked_question": asked,
            "trait_used": None,
            "validation": validation,
            "persona_version": deps.settings.persona_version,
        },
    }
    return TurnState(final_state=final_state)


def _json_safe_decisions(decisions):
    if not decisions:
        return decisions
    out = dict(decisions)
    sig = out.get("persona_signals")
    if isinstance(sig, PersonaSignals):
        out["persona_signals"] = asdict(sig)
    return out
