from agent.persona.constants.modes import Mode
from agent.persona.directive import TurnDirective
from agent.policy.validation import validate_reply


def _directive(**overrides) -> TurnDirective:
    base = dict(
        mode=Mode.EVERYDAY,
        length_band=(3, 25),
        max_bubbles=3,
        question_allowed=True,
        advice_allowed=False,
        humor_allowed=True,
        callback_allowed=True,
        trait_allowed=False,
        concern_tier="normal",
        dependency_level=0,
        stage=1,
        closing_signal=False,
        reason_codes=(),
    )
    base.update(overrides)
    return TurnDirective(**base)


def _codes(reply, **kw):
    kw.setdefault("user_message", "")
    kw.setdefault("user_used_emoji", False)
    kw.setdefault("user_started_pet_name", False)
    result = validate_reply(reply, _directive(**kw.pop("directive_overrides", {})), **kw)
    return {v.code for v in result.violations}


def test_detects_banned_phrase():
    assert "banned_phrase" in _codes("I hear you. How are you?")


def test_detects_affect_claim():
    assert "affect_claim" in _codes("I missed you.")


def test_allows_exchange_scoped_affect():
    assert "affect_claim" not in _codes("Good to hear from you. What's been going on?")


def test_detects_too_many_questions():
    assert "too_many_questions" in _codes("What happened? And how are you?")


def test_blocks_questions_when_budget_is_zero():
    assert "too_many_questions" in _codes("What happened?", directive_overrides={"question_allowed": False})


def test_detects_markdown_list():
    assert "markdown_list" in _codes("- first\n- second")


def test_detects_stage_language_leak():
    assert "stage_language_leak" in _codes("Your relationship is at stage 2 now.")


def test_detects_dependency_language_leak():
    assert "dependency_language_leak" in _codes("You're getting dependent on me.")


def test_safety_reply_bypasses_validation():
    result = validate_reply(
        "I want to make sure you're safe right now. Are you thinking about ending your life, or in danger right now?",
        _directive(),
        user_message="i want to die",
        user_used_emoji=False,
        user_started_pet_name=False,
        is_safety_reply=True,
    )
    assert result.violations == ()


def test_user_echoed_banned_phrase_is_not_reported():
    codes = _codes(
        'She kept saying "I hear you" and it got to me.',
        user_message='She kept saying "I hear you"',
    )
    assert "banned_phrase" not in codes


def test_counts_questions_in_reply():
    result = validate_reply("What happened? Where were you?", _directive(), user_message="x", user_used_emoji=False, user_started_pet_name=False)
    assert result.asked_question is True
