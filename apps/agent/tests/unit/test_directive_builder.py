from agent.persona.constants.dials import Dials
from agent.persona.constants.modes import Mode
from agent.policy.directive import build_directive
from agent.policy.modes import ModeDecision

DIALS = Dials(formality=2, warmth=7, directness=6, humor=4, initiative=3)


def _build(**overrides):
    base = dict(  # noqa: C408
        mode_decision=ModeDecision(mode=Mode.EVERYDAY, reason="everyday"),
        dials=DIALS,
        stage=1,
        dependency_level=0,
        concern_tier="normal",
        recent_turns=(),
        user_message="hello there",
        user_used_emoji=False,
        user_started_pet_name=False,
        distress_last_two_turns=False,
        playful_last_four_turns=0,
        trait_available=False,
        trait_pending_reaction=False,
    )
    base.update(overrides)
    return build_directive(**base)


def test_question_allowed_by_default():
    assert _build().question_allowed is True


def test_two_questions_in_last_four_turns_blocks_questions():
    turns = [
        {"asked_question": True, "mode": "everyday"},
        {"asked_question": True, "mode": "everyday"},
        {"asked_question": False, "mode": "everyday"},
    ]
    d = _build(recent_turns=turns)
    assert d.question_allowed is False
    assert "question_budget_two_questions" in d.reason_codes


def test_closing_signal_blocks_questions():
    d = _build(user_message="ok")
    assert d.question_allowed is False
    assert "question_budget_closing_signal" in d.reason_codes


def test_listen_denies_advice():
    d = _build(mode_decision=ModeDecision(mode=Mode.LISTEN, reason="venting"))
    assert d.advice_allowed is False


def test_decide_allows_advice():
    d = _build(mode_decision=ModeDecision(mode=Mode.DECIDE, reason="asking_decision"))
    assert d.advice_allowed is True


def test_distress_denies_humor():
    d = _build(distress_last_two_turns=True)
    assert d.humor_allowed is False
    assert "humor_denied_distress" in d.reason_codes


def test_humor_dial_zero_denies_humor():
    d = _build(dials=Dials(formality=2, warmth=7, directness=6, humor=0, initiative=3))
    assert d.humor_allowed is False


def test_trait_allowed_only_in_everyday_and_banter():
    assert _build(trait_available=True).trait_allowed is True
    d = _build(
        trait_available=True,
        mode_decision=ModeDecision(mode=Mode.LISTEN, reason="venting"),
    )
    assert d.trait_allowed is False


def test_pending_trait_reaction_blocks_trait_use():
    d = _build(trait_available=True, trait_pending_reaction=True)
    assert d.trait_allowed is False
    assert "trait_denied_pending_reaction" in d.reason_codes


def test_length_band_follows_mode():
    d = _build(mode_decision=ModeDecision(mode=Mode.LISTEN, reason="venting"))
    assert d.length_band == (8, 25)
    assert d.max_bubbles == 3
