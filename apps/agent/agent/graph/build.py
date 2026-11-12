from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from agent.graph import nodes
from agent.graph.state import TurnState


def build_turn_graph(*, checkpointer: BaseCheckpointSaver):
    graph = StateGraph(TurnState)
    graph.add_node("classify_parallel", nodes.classify_parallel)
    graph.add_node("apply_thread_policy", nodes.apply_thread_policy)
    graph.add_node("plan_memory", nodes.plan_memory)
    graph.add_node("retrieve_and_load_state", nodes.retrieve_and_load_state)
    graph.add_node("build_directive_node", nodes.build_directive_node)
    graph.add_node("respond_safety", nodes.respond_safety_node)
    graph.add_node("respond_concern", nodes.respond_concern_node)
    graph.add_node("assemble_and_generate", nodes.assemble_and_generate)
    graph.add_node("validate_reply_node", nodes.validate_reply_node)
    graph.add_node("persist_turn", nodes.persist_turn)

    graph.add_edge(START, "classify_parallel")
    graph.add_edge("classify_parallel", "apply_thread_policy")
    graph.add_edge("apply_thread_policy", "plan_memory")
    graph.add_edge("plan_memory", "retrieve_and_load_state")
    graph.add_edge("retrieve_and_load_state", "build_directive_node")
    graph.add_conditional_edges(
        "build_directive_node",
        nodes.route_after_directive,
        {
            "respond_safety": "respond_safety",
            "respond_concern": "respond_concern",
            "assemble_and_generate": "assemble_and_generate",
        },
    )
    graph.add_edge("respond_safety", "persist_turn")
    graph.add_edge("respond_concern", "persist_turn")
    graph.add_edge("assemble_and_generate", "validate_reply_node")
    graph.add_edge("validate_reply_node", "persist_turn")
    graph.add_edge("persist_turn", END)

    return graph.compile(checkpointer=checkpointer)
