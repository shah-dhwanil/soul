from agent.pg.models import TraitStatus
from agent.policy.traits import observe_trait, trait_is_sensitive, trial_allowed


def test_neutral_reaction_never_promotes():
    m = observe_trait(
        kind="shared_language",
        label="the Sunday dread",
        status="noticed",
        positive_count=0,
        negative_count=0,
        neutral_count=3,
        distinct_days=3,
        reaction="neutral",
        sensitive=False,
    )
    assert m.promoted is False


def test_positive_reaction_promotes_to_candidate():
    m = observe_trait(
        kind="shared_language",
        label="the Sunday dread",
        status="noticed",
        positive_count=1,
        negative_count=0,
        neutral_count=1,
        distinct_days=2,
        reaction="positive",
        sensitive=False,
    )
    assert m.status is TraitStatus.CANDIDATE
    assert m.promoted is True


def test_two_negative_reactions_retire():
    m = observe_trait(
        kind="running_joke",
        label="gallows time",
        status="active",
        positive_count=3,
        negative_count=2,
        neutral_count=0,
        distinct_days=4,
        reaction="negative",
        sensitive=False,
    )
    assert m.status is TraitStatus.RETIRED
    assert m.retired is True


def test_sensitive_topics_never_become_traits():
    assert trait_is_sensitive("my knee injury", "my knee injury is back") is True
    assert trait_is_sensitive("the 3pm gallows", "the 3pm gallows again") is False


def test_trial_only_in_everyday_and_banter():
    assert trial_allowed("everyday") is True
    assert trial_allowed("banter") is True
    for mode in ("listen", "ground", "safety", "repair", "explore", "decide"):
        assert trial_allowed(mode) is False
