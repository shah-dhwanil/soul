"""Graphiti ontology: node types, edge types, and person alias handling."""

from agent.graphiti.aliases import (
    PersonAliasResolver,
    merge_aliases,
    normalize_person_name,
)
from agent.graphiti.edge import (
    EDGE_TYPE_MAP,
    EDGE_TYPES,
    HasDate,
    HasGoal,
    HasPreference,
    Relationship,
)
from agent.graphiti.entity import (
    ENTITY_TYPES,
    Date,
    Event,
    Goal,
    Person,
    Preference,
    User,
)
from agent.graphiti.episode import (
    CUSTOM_EXTRACTION_INSTRUCTIONS,
    SHORT_USER_MESSAGE_WORDS,
    IngestTurn,
    build_episode_body,
)

__all__ = [
    "CUSTOM_EXTRACTION_INSTRUCTIONS",
    "Date",
    "EDGE_TYPE_MAP",
    "EDGE_TYPES",
    "ENTITY_TYPES",
    "Event",
    "Goal",
    "HasDate",
    "HasGoal",
    "HasPreference",
    "Person",
    "PersonAliasResolver",
    "Preference",
    "Relationship",
    "User",
    "IngestTurn",
    "SHORT_USER_MESSAGE_WORDS",
    "build_episode_body",
    "merge_aliases",
    "normalize_person_name",
]
