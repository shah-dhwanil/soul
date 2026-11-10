"""Synthetic multi-turn conversations for end-to-end agent evaluation."""

from dataclasses import dataclass

from agent.history import PriorTurn


@dataclass(frozen=True)
class EvalTurn:
    user_message: str
    rubric: str
    must_not_contain: tuple[str, ...] = ()
    max_questions: int | None = 1


@dataclass(frozen=True)
class ConversationScenario:
    id: str
    description: str
    turns: tuple[EvalTurn, ...]
    seed_prior: tuple[PriorTurn, ...] = ()


CONVERSATION_SCENARIOS: tuple[ConversationScenario, ...] = (
    ConversationScenario(
        id="gujarati_casual_greeting",
        description="Casual Hinglish/Gujarati greeting; no therapy or dictionary mode.",
        turns=(
            EvalTurn(
                user_message="Su kare che bro",
                rubric=(
                    "Reply like a friend texting back: short, casual, matches the user's "
                    "language/register (Gujarati/Hinglish OK). No life-coaching, no steps "
                    "or homework. No stock empathy or cheerleading. At most one light "
                    "question or none."
                ),
                must_not_contain=(
                    "I hear you",
                    "You've got this",
                    "small step",
                    "unpack",
                ),
            ),
        ),
    ),
    ConversationScenario(
        id="english_small_talk",
        description="Low-stakes check-in should not pull memory or over-question.",
        turns=(
            EvalTurn(
                user_message="hey",
                rubric=(
                    "Brief warm greeting back, human tone, no assistant boilerplate, "
                    "no multiple questions."
                ),
                max_questions=1,
            ),
        ),
    ),
    ConversationScenario(
        id="vent_listen",
        description="User venting; Wren stays with it and does not fix.",
        turns=(
            EvalTurn(
                user_message="I'm so done with work today, everyone wants something from me",
                rubric=(
                    "Venting mode: validate without fixing, no bullet plans, no "
                    "'have you considered' coaching. Specific to what they said. "
                    "No banned stock phrases."
                ),
                must_not_contain=("Have you considered", "small step", "I hear you"),
            ),
        ),
    ),
    ConversationScenario(
        id="follow_up_with_history",
        description="Pronoun follow-up after established context.",
        seed_prior=(
            PriorTurn(
                user_message="My chemistry exam is on Friday and I'm nervous.",
                agent_response="Friday's close. What's the bit that's got you most on edge?",
            ),
        ),
        turns=(
            EvalTurn(
                user_message="She said I should just relax",
                rubric=(
                    "Uses chat context (exam/nervous) without inventing names. "
                    "One clear read, not preachy. 'She' refers to someone from context "
                    "or asks one clarifying question if needed — not both piled on."
                ),
            ),
        ),
    ),
    ConversationScenario(
        id="good_news",
        description="Celebrate specifically; do not pivot to next goal.",
        turns=(
            EvalTurn(
                user_message="I got the internship offer!",
                rubric=(
                    "Specific gladness about the internship, no 'what's next' pivot, "
                    "no cheerleader clichés like 'so proud' or 'you've got this'."
                ),
                must_not_contain=("proud of you", "You've got this", "what's next"),
            ),
        ),
    ),
)
