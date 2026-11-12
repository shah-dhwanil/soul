from agent.policy.concern import (
    ConcernTier,
    build_boundary_reply,
    build_concern_reply,
    build_safety_reply,
    extract_concern_quote,
)


def test_concern_tier_values():
    assert ConcernTier.NORMAL.value == "normal"
    assert ConcernTier.CONCERN.value == "concern"
    assert ConcernTier.ACUTE.value == "acute"


def test_extracts_quoted_phrase_from_buried_disclosure():
    message = "some nights I think everyone would be honestly better off without me. anyway, work was fine."
    quote = extract_concern_quote(message)
    assert quote is not None
    assert "better off without me" in quote


def test_returns_none_when_no_concern_phrase():
    assert extract_concern_quote("work was fine, the deploy went out at 4") is None


def test_concern_reply_quotes_the_user():
    reply = build_concern_reply(
        "everyone would be better off without me. anyway, work was fine.", "en-US"
    )
    assert "better off without me" in reply
    assert "suicide" in reply.lower()


def test_concern_reply_without_quote_still_asks_directly():
    reply = build_concern_reply("what's the point", "en-US")
    assert "suicide" in reply.lower()


def test_concern_reply_has_no_advice_or_silver_lining():
    reply = build_concern_reply("everyone would be better off without me", "en-US")
    lowered = reply.lower()
    for forbidden in (
        "have you considered",
        "it gets better",
        "at least",
        "on the bright side",
    ):
        assert forbidden not in lowered


def test_safety_reply_contains_resolved_resources():
    reply = build_safety_reply("en-US")
    assert "988" in reply
    assert "Are you thinking about ending your life" in reply


def test_safety_reply_for_unknown_locale_uses_generic_resources():
    reply = build_safety_reply("zz-ZZ")
    assert "988" not in reply
    assert "local emergency number" in reply


def test_boundary_replies_never_only_decline():
    for kind in (
        "only_friend",
        "partner_jealousy",
        "therapy_diagnosis",
        "professional_advice",
    ):
        reply = build_boundary_reply(kind, locale="en-US")
        assert len(reply.split(".")) >= 3, kind


def test_only_friend_boundary_is_the_spec_line():
    reply = build_boundary_reply("only_friend")
    assert reply.startswith("I'm glad you can land here.")
    assert "Who else has your back" in reply
