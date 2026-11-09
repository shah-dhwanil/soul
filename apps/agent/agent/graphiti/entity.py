"""Custom Graphiti entity (node) types for the Wren memory graph.

Graphiti extracts and updates these nodes from ingested episodes. Class
docstrings and field descriptions are prompt material for the extraction model,
so they stay short, contrast each type against its neighbours, and use explicit
dates only. Enum-like fields use plain strings with the allowed values
described in text to keep the JSON schema reliable for smaller models.

Time-varying facts (relationship quality, preference sentiment, goal status)
live on edges, not on these nodes.

Typed node models intentionally avoid optional scalar fields: Graphiti flattens
attribute extraction onto Neo4j properties, and the Neo4j 6 driver rejects unset
optional values (NO_VALUE). Put dates and outcomes in the node name or edge facts.
"""

from pydantic import BaseModel


class User(BaseModel):
    """The owner of this memory graph, usually the person speaking in the ingested messages.

    Not a Person: never create a Person node for the graph owner. Example: the user
    saying "I started learning Spanish" is the User, not a Person.

    Put the user's name on the node name, not in typed attributes.
    """


class Person(BaseModel):
    """A particular other person in the user's life, such as family, a friend, partner, or coworker.

    Not the User, not an organization, and not the AI assistant (Wren). Example:
    Sunita, also called Mom and Mama, is one Person node. Put nicknames in the node
    name or rely on Graphiti deduplication; do not store alias lists as node properties.
    """


class Event(BaseModel):
    """Something that happened or will happen at a specific time, such as an exam, trip, argument, or appointment.

    Not a Goal (no fixed time) and not a Preference (a standing taste). Put
    distinguishing detail and explicit dates in the name, e.g. "Chemistry exam, 2026-11-13",
    so repeated events do not merge. Example: "Dinner with Sunita on 2026-11-13".
    Never use relative dates in the name; resolve from episode timestamps or omit.
    """


class Date(BaseModel):
    """A recurring or important explicit calendar date.

    Not a one-off event (use an Event node) and not a Person. Put the explicit date
    in the node name, e.g. "Sunita birthday 1990-03-15 recurring". Never use relative
    expressions.
    """


class Preference(BaseModel):
    """A thing the user has a standing like, dislike, habit, or recurring choice about, such as chai or morning walks.

    The sentiment and its history live on the HasPreference edge, not on this node.
    Not a one-off choice and not an Event. Example: node name "chai".
    """


class Goal(BaseModel):
    """An ongoing pursuit or aspiration the user is working toward, such as learning Spanish.

    Status and progress live on the HasGoal edge, not on this node. Not a one-off
    Event (a Goal has no fixed time) and not a casual topic. Example: "learning Spanish".
    """


ENTITY_TYPES: dict[str, type[BaseModel]] = {
    "User": User,
    "Person": Person,
    "Event": Event,
    "Date": Date,
    "Preference": Preference,
    "Goal": Goal,
}
