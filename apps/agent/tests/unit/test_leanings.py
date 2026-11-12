from agent.pg.models import LeaningStatus
from agent.policy.leanings import observe_leaning


def test_humor_style_candidate_needs_three_positives_over_three_days():
    m = observe_leaning(
        kind="humor_style",
        value="deadpan",
        status="noticed",
        positive_count=3,
        negative_count=1,
        distinct_days=3,
        engagement_at_or_above_baseline=True,
    )
    assert m.status is LeaningStatus.CANDIDATE


def test_two_negative_reactions_retire_a_leaning():
    m = observe_leaning(
        kind="humor_style",
        value="absurd",
        status="active",
        positive_count=5,
        negative_count=2,
        distinct_days=6,
        engagement_at_or_above_baseline=True,
    )
    assert m.status is LeaningStatus.RETIRED


def test_engagement_below_baseline_does_not_promote_to_active():
    m = observe_leaning(
        kind="curiosity_topic",
        value="sailing",
        status="tilt",
        positive_count=3,
        negative_count=0,
        distinct_days=3,
        engagement_at_or_above_baseline=False,
    )
    assert m.status is LeaningStatus.TILT
    assert m.promoted is False
