from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from agent.graph import nodes
from agent.graph.state import TurnState


def build_turn_graph(*, checkpointer: BaseCheckpointSaver):
    graph = StateGraph(TurnState)
    graph.add_node("classify_parallel", nodes.classify_parallel)
    graph.add_node("apply_thread_policy", nodes.apply_thread_policy)
    graph.add_node("plan_memory", nodes.plan_memory)
    graph.add_node("retrieve_memory", nodes.retrieve_memory)
    graph.add_node("assemble_and_generate", nodes.assemble_and_generate)
    graph.add_node("persist_turn", nodes.persist_turn)

    graph.add_edge(START, "classify_parallel")
    graph.add_edge("classify_parallel", "apply_thread_policy")
    graph.add_edge("apply_thread_policy", "plan_memory")
    graph.add_conditional_edges(
        "plan_memory",
        nodes.route_memory,
        {
            "retrieve_memory": "retrieve_memory",
            "assemble_and_generate": "assemble_and_generate",
        },
    )
    graph.add_edge("retrieve_memory", "assemble_and_generate")
    graph.add_edge("assemble_and_generate", "persist_turn")
    graph.add_edge("persist_turn", END)

    return graph.compile(checkpointer=checkpointer)
