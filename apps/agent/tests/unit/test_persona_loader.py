import dataclasses

import pytest
from agent.persona.loader import PersonaDriftError, assert_no_drift, load_persona


def test_loads_bundle_with_matching_hash():
    bundle = load_persona()
    assert bundle.version == "wren-2.2"
    assert len(bundle.prompt_sha256) == 64
    assert bundle.prompt.startswith("You are Wren")


def test_manifest_hash_matches_prompt_file():
    bundle = load_persona()
    assert_no_drift(bundle)


def test_drift_raises_when_hash_differs():
    # PersonaBundle is frozen, so build a modified copy rather than monkeypatching.
    bundle = dataclasses.replace(load_persona(), prompt_sha256="0" * 64)
    with pytest.raises(PersonaDriftError):
        assert_no_drift(bundle)


def test_prompt_declares_only_known_placeholders():
    import re

    from agent.persona.template import PLACEHOLDER_NAMES

    bundle = load_persona()
    found = set(re.findall(r"\{\{(\w+)\}\}", bundle.prompt))
    assert found <= set(PLACEHOLDER_NAMES)
    assert found == set(PLACEHOLDER_NAMES)


def test_prompt_never_contains_memory_context_placeholder():
    bundle = load_persona()
    assert "{{memory_context}}" not in bundle.prompt


def test_asset_hash_is_stable():
    assert load_persona().asset_hash == load_persona().asset_hash
