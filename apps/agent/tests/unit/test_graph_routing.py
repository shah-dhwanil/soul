from langgraph.checkpoint.memory import MemorySaver

from agent.graph.build import build_turn_graph
from agent.graph.nodes import route_memory
from agent.graph.state import TurnState


def test_route_memory_when_required() -> None:
    assert (
        route_memory(
            TurnState(memory_required=True, memory_queries=["someone birthday"])
        )
        == "retrieve_memory"
    )
    assert route_memory(TurnState(memory_required=True, memory_queries=[])) == (
        "assemble_and_generate"
    )
    assert route_memory(TurnState(memory_required=False)) == "assemble_and_generate"
    assert (
        route_memory(
            TurnState(
                memory_required=False,
                memory_queries=["interview Friday"],
            )
        )
        == "retrieve_memory"
    )


def test_graph_compiles_with_memory_saver() -> None:
    graph = build_turn_graph(checkpointer=MemorySaver())
    assert graph is not None


def test_route_after_directive() -> None:
    from agent.graph.nodes import route_after_directive

    assert route_after_directive(TurnState(concern_tier="acute")) == "respond_safety"
    assert route_after_directive(TurnState(concern_tier="concern")) == "respond_concern"
    assert (
        route_after_directive(
            TurnState(concern_tier="concern", concern_asked_this_episode=True)
        )
        == "assemble_and_generate"
    )
    assert route_after_directive(TurnState(concern_tier="normal")) == (
        "assemble_and_generate"
    )
