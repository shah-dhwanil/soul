from datetime import UTC, datetime

from pydantic import BaseModel

from agent.graphiti import (
    CUSTOM_EXTRACTION_INSTRUCTIONS,
    EDGE_TYPE_MAP,
    EDGE_TYPES,
    ENTITY_TYPES,
    Date,
    Event,
    Goal,
    HasDate,
    HasGoal,
    HasPreference,
    IngestTurn,
    Person,
    PersonAliasResolver,
    Preference,
    Relationship,
    User,
    build_episode_body,
    merge_aliases,
    normalize_person_name,
)


def test_entity_types_register_all_ontology_nodes() -> None:
    assert set(ENTITY_TYPES) == {"User", "Person", "Event", "Date", "Preference", "Goal"}
    assert all(issubclass(model, BaseModel) for model in ENTITY_TYPES.values())
    assert ENTITY_TYPES["User"] is User
    assert ENTITY_TYPES["Person"] is Person
    assert ENTITY_TYPES["Goal"] is Goal


def test_person_has_no_typed_attribute_fields() -> None:
    assert Person.model_fields == {}


def test_person_docstring_excludes_the_assistant() -> None:
    docstring = (Person.__doc__ or "").lower()
    assert "wren" in docstring
    assert "assistant" in docstring


def test_user_has_no_typed_attribute_fields() -> None:
    assert User.model_fields == {}


def test_event_has_no_typed_attribute_fields() -> None:
    assert Event.model_fields == {}


def test_event_docstring_requires_explicit_dates() -> None:
    docstring = (Event.__doc__ or "").lower()
    assert "explicit" in docstring
    assert "relative" in docstring


def test_date_has_no_typed_attribute_fields() -> None:
    assert Date.model_fields == {}


def test_date_docstring_has_no_relative_date_examples() -> None:
    docstring = Date.__doc__ or ""
    assert "next Friday" not in docstring
    assert "last March" not in docstring


def test_preference_sentiment_is_documented_on_edge_type() -> None:
    assert "sentiment" not in Preference.model_fields
    assert HasPreference.model_fields == {}
    assert "fact" in (HasPreference.__doc__ or "").lower()


def test_goal_status_is_documented_on_edge_type() -> None:
    assert "status" not in Goal.model_fields
    assert HasGoal.model_fields == {}
    assert "status" in (HasGoal.__doc__ or "").lower()


def test_edge_types_have_no_typed_attribute_fields() -> None:
    assert Relationship.model_fields == {}
    assert HasDate.model_fields == {}
    assert HasPreference.model_fields == {}
    assert HasGoal.model_fields == {}


def test_edge_types_register_all_relationship_edges() -> None:
    assert EDGE_TYPES == {
        "Relationship": Relationship,
        "HasPreference": HasPreference,
        "HasGoal": HasGoal,
        "HasDate": HasDate,
    }


def test_edge_type_map_is_tightened_without_wildcards() -> None:
    assert EDGE_TYPE_MAP == {
        ("User", "Person"): ["Relationship"],
        ("Person", "User"): ["Relationship"],
        ("Person", "Person"): ["Relationship"],
        ("User", "Preference"): ["HasPreference"],
        ("Preference", "User"): ["HasPreference"],
        ("User", "Goal"): ["HasGoal"],
        ("Goal", "User"): ["HasGoal"],
        ("User", "Date"): ["HasDate"],
        ("Person", "Date"): ["HasDate"],
        ("Event", "Date"): ["HasDate"],
        ("Preference", "Date"): ["HasDate"],
        ("Goal", "Date"): ["HasDate"],
        ("Date", "User"): ["HasDate"],
        ("Date", "Person"): ["HasDate"],
        ("Date", "Event"): ["HasDate"],
        ("Date", "Preference"): ["HasDate"],
        ("Date", "Goal"): ["HasDate"],
    }
    assert ("Entity", "Person") not in EDGE_TYPE_MAP
    assert not any("Entity" in pair for pair in EDGE_TYPE_MAP)


def test_date_can_be_related_to_every_entity_type() -> None:
    entity_names = {"User", "Person", "Event", "Preference", "Goal"}
    for name in entity_names:
        assert EDGE_TYPE_MAP[(name, "Date")] == ["HasDate"]
        assert EDGE_TYPE_MAP[("Date", name)] == ["HasDate"]


def test_normalize_person_name_is_case_and_whitespace_insensitive() -> None:
    assert normalize_person_name("  Mama  ") == "mama"
    assert normalize_person_name("SUNITA") == "sunita"
    assert normalize_person_name("Mary   Jane") == "mary jane"


def test_alias_resolver_resolves_variants_to_one_canonical() -> None:
    resolver = PersonAliasResolver()
    resolver.register("Sunita", ["Mom", "Mama"])

    assert resolver.resolve("Sunita") == "Sunita"
    assert resolver.resolve("mom") == "Sunita"
    assert resolver.resolve("  MAMA ") == "Sunita"
    assert resolver.resolve("mama") == "Sunita"


def test_alias_resolver_returns_normalized_name_when_unknown() -> None:
    resolver = PersonAliasResolver()

    assert resolver.resolve("  Alex ") == "alex"


def test_alias_resolver_aliases_for_returns_original_aliases() -> None:
    resolver = PersonAliasResolver()
    resolver.register("Sunita", ["Mom", "Mama", "mom"])

    assert resolver.aliases_for("Sunita") == ["Mom", "Mama"]
    assert resolver.aliases_for("nobody") == []


def test_merge_aliases_is_a_no_op_on_person_nodes() -> None:
    person = Person()
    assert merge_aliases(person, ["Mama", "mom", "Mom"]) is person


def test_calendar_hint_resolves_next_monday_from_anchor() -> None:
    from datetime import UTC, datetime

    from agent.graphiti.episode import calendar_hint_line, resolve_next_monday

    anchor = datetime(2026, 11, 10, 14, 51, 57, tzinfo=UTC)
    assert resolve_next_monday(anchor).isoformat() == "2026-11-16"
    hint = calendar_hint_line(anchor)
    assert "2026-11-16" in hint
    assert "REFERENCE_CALENDAR" in hint


def test_extraction_instructions_guard_the_assistant_and_relative_dates() -> None:
    text = CUSTOM_EXTRACTION_INSTRUCTIONS.lower()

    assert "wren" in text
    assert "assistant" in text
    assert "relative" in text


def test_episode_body_adds_assistant_context_for_short_replies() -> None:
    t0 = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
    t1 = datetime(2026, 11, 13, 9, 1, tzinfo=UTC)
    t2 = datetime(2026, 11, 13, 9, 2, tzinfo=UTC)
    body = build_episode_body(
        [
            IngestTurn("user", "My chemistry exam is on Friday.", t0),
            IngestTurn("Wren", "How did the exam go?", t1),
            IngestTurn("user", "Pretty well.", t2, is_reply=True),
        ]
    )

    assert "Wren:" not in body
    assert "Assistant asked: How did the exam go?" in body
    assert "user: Pretty well." in body
    assert "user: My chemistry exam is on Friday." in body
    assert body.index("Assistant asked") < body.index("user: Pretty well.")


def test_episode_body_skips_assistant_context_for_long_user_messages() -> None:
    t0 = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
    t1 = datetime(2026, 11, 13, 9, 1, tzinfo=UTC)
    t2 = datetime(2026, 11, 13, 9, 2, tzinfo=UTC)
    long_user = (
        "I told Sunita about the exam and she said she is proud of me for studying."
    )
    body = build_episode_body(
        [
            IngestTurn("user", "My chemistry exam is on Friday.", t0),
            IngestTurn("assistant", "How did the exam go?", t1),
            IngestTurn("user", long_user, t2),
        ]
    )

    assert "Assistant asked" not in body
    assert long_user in body
