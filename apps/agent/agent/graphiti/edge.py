"""Custom Graphiti edge (relationship) types for the Wren memory graph.

Time-varying facts live here rather than on nodes. Graphiti's temporal edges
track when each value became true and when it was superseded, so relationship
quality, preference sentiment, and goal status keep an as-of history.

The ontology stores the user's standing relationships as edges from the User
node to a Person node. Person-to-Person edges are also allowed because the
graph owner can relate two other people. Reverse pairs are registered too,
because extraction may emit an edge in either direction and Graphiti does not
guarantee that a reversed triplet matches the forward map entry.

Typed edge models use empty bodies so Neo4j is not given unset optional
attribute maps (NO_VALUE). The edge ``fact`` string is the source of truth.
"""

from pydantic import BaseModel


class Relationship(BaseModel):
    """A standing relationship between the user or another person and a person.

    Not a one-off interaction: an argument or dinner is an Event, not a Relationship.
    Put relation and quality in the edge fact text. Example: User is Sunita's son;
    relationship quality strained.
    """


class HasPreference(BaseModel):
    """A standing like, dislike, habit, or recurring choice the user has about a Preference.

    Put sentiment in the edge fact text. Example: User likes masala chai.
    """


class HasGoal(BaseModel):
    """The user's current relationship to a Goal, including its status.

    Put status in the edge fact text. Example: User is actively learning Spanish.
    """


class HasDate(BaseModel):
    """A link between any entity and a Date that anchors it.

    Put the relation in the edge fact text. Example: Chemistry exam occurs on 2026-11-13.
    """


EDGE_TYPES: dict[str, type[BaseModel]] = {
    "Relationship": Relationship,
    "HasPreference": HasPreference,
    "HasGoal": HasGoal,
    "HasDate": HasDate,
}

_DATE_ENTITIES: tuple[str, ...] = ("User", "Person", "Event", "Preference", "Goal")

EDGE_TYPE_MAP: dict[tuple[str, str], list[str]] = {
    ("User", "Person"): ["Relationship"],
    ("Person", "User"): ["Relationship"],
    ("Person", "Person"): ["Relationship"],
    ("User", "Preference"): ["HasPreference"],
    ("Preference", "User"): ["HasPreference"],
    ("User", "Goal"): ["HasGoal"],
    ("Goal", "User"): ["HasGoal"],
    **{(entity, "Date"): ["HasDate"] for entity in _DATE_ENTITIES},
    **{("Date", entity): ["HasDate"] for entity in _DATE_ENTITIES},
}
