from agent.model.memory_queries import parse_memory_query_response


def test_parse_empty_array() -> None:
    assert parse_memory_query_response("[]") == []
    assert parse_memory_query_response('Here: []') == []


def test_parse_valid_queries() -> None:
    raw = '["Riya exam Friday", "chemistry exam"]'
    assert parse_memory_query_response(raw) == ["Riya exam Friday", "chemistry exam"]


def test_parse_no_json_returns_empty() -> None:
    assert parse_memory_query_response("no queries needed") == []


def test_parse_limits_to_three() -> None:
    raw = '["a", "b", "c", "d"]'
    assert parse_memory_query_response(raw) == ["a", "b", "c"]


def test_route_memory_skips_empty_queries() -> None:
    from agent.graph.nodes import route_memory
    from agent.graph.state import TurnState

    assert (
        route_memory(TurnState(memory_required=True, memory_queries=[]))
        == "assemble_and_generate"
    )
    assert (
        route_memory(TurnState(memory_required=True, memory_queries=["exam"]))
        == "retrieve_memory"
    )
