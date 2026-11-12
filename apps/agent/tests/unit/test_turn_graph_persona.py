from langgraph.checkpoint.memory import MemorySaver

from agent.graph.build import build_turn_graph
from agent.graph.state import initial_state
from agent.persona.constants.modes import Mode


def test_graph_compiles_with_new_nodes():
    graph = build_turn_graph(checkpointer=MemorySaver())
    assert graph is not None


def test_state_defaults_carry_persona_fields():
    state = initial_state(
        user_id="u1",
        turn_id="00000000-0000-0000-0000-000000000000",
        db_thread_id="00000000-0000-0000-0000-000000000001",
        user_message="hi",
        decision_history=[],
    )
    assert state["concern_tier"] == "normal"
    assert state["reply_source"] == ""
    assert state["mode"] == ""


def test_mode_is_recorded_on_state():
    from agent.graph.state import TurnState

    state = TurnState(mode=Mode.LISTEN.value, reply_source="model")
    assert state["mode"] == "listen"
