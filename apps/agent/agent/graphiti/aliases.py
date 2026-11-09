"""Deterministic person alias handling.

Graphiti's LLM-based entity resolution is the primary mechanism for merging
duplicate people, but the ontology requires a maintained alias list as a
backstop. This module is the pure, persistence-free seam for that list; a
Postgres-backed store can wrap ``PersonAliasResolver`` later without changing
callers.
"""

from agent.graphiti.entity import Person


def normalize_person_name(name: str) -> str:
    """Lowercase a name and collapse internal whitespace for comparison."""
    return " ".join(name.split()).lower()


class PersonAliasResolver:
    """Resolve names and nicknames to a single canonical person name."""

    def __init__(self) -> None:
        self._canonical_by_key: dict[str, str] = {}
        self._aliases_by_canonical: dict[str, list[str]] = {}

    def register(self, canonical: str, aliases: list[str]) -> None:
        key = normalize_person_name(canonical)
        self._canonical_by_key[key] = canonical

        known = self._aliases_by_canonical.setdefault(key, [])
        seen = {normalize_person_name(canonical)}
        seen.update(normalize_person_name(alias) for alias in known)

        for alias in aliases:
            alias_key = normalize_person_name(alias)
            if not alias_key or alias_key in seen:
                continue
            seen.add(alias_key)
            known.append(alias)
            self._canonical_by_key[alias_key] = canonical

    def resolve(self, name: str) -> str:
        key = normalize_person_name(name)
        return self._canonical_by_key.get(key, key)

    def aliases_for(self, canonical: str) -> list[str]:
        key = normalize_person_name(canonical)
        return list(self._aliases_by_canonical.get(key, []))


def merge_aliases(person: Person, aliases: list[str]) -> Person:
    """No-op: aliases are resolved via ``PersonAliasResolver``, not node properties."""
    del aliases
    return person
