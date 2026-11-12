from typing import Any

from langchain_cloudflare import CloudflareWorkersAIDecisionModel

from agent.config import Settings
from agent.decision_parsing import parse_persona_signals, parse_thread_and_memory
from agent.history import ChatTurn, format_turns_for_clef


class DecisionModel:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = CloudflareWorkersAIDecisionModel(
            model_name=settings.clef_model,  # type: ignore[arg-type]
            account_id=settings.cf_account_id,
            api_token=settings.cf_ai_api_token,
        )

    @staticmethod
    def thread_continue_question() -> dict[str, Any]:
        return {
            "thread_continue": {
                "type": "noul",
                "instructions": (
                    "Is the user's latest message part of the same ongoing "
                    "conversation as the recent turns above (same chat session, "
                    "follow-up, small talk, or callback), rather than a clearly "
                    "unrelated new topic or explicit fresh start?"
                ),
            }
        }

    @staticmethod
    def recent_context_required_question() -> dict[str, Any]:
        return {
            "recent_context_required": {
                "type": "noul",
                "instructions": (
                    "Would a good reply depend on specific details in the "
                    "recent turns above (references, follow-ups, unresolved "
                    "thread)?"
                ),
            }
        }

    @staticmethod
    def is_memory_required_question() -> dict[str, Any]:
        return {
            "memory_required": {
                "type": "noul",
                "instructions": (
                    "Should a reply use facts looked up from long-term memory "
                    "about this user? Answer yes when the latest message (with "
                    "recent context) mentions retrievable personal context: "
                    "jobs or interviews, exams, relationships, dates or places, "
                    "goals, preferences, or ongoing situations—including "
                    "updates (rescheduled, cancelled, moved, offer, etc.) even "
                    "if the user is informing rather than asking. Answer no for "
                    "greetings, filler, pure venting with no lookup target, or "
                    "banter with no named entity, event, or plan."
                ),
            }
        }

    @staticmethod
    def analyze_user_chat() -> dict[str, Any]:
        return {
            "user_emotion": {
                "type": "score",
                "instructions": "Analyze the user's emotion in the current message.",
                "criteria": [
                    "neutral",
                    "happy",
                    "sad",
                    "anxious",
                    "frustrated",
                ],
            }
        }

    @staticmethod
    def agent_emotion() -> dict[str, Any]:
        return {
            "agent_emotion": {
                "type": "score",
                "instructions": (
                    "What tone should the assistant use in the reply?"
                ),
                "criteria": [
                    "warm",
                    "calm",
                    "playful",
                    "direct",
                    "supportive",
                ],
            }
        }

    @staticmethod
    def concern_tier_question() -> dict[str, Any]:
        return {
            "concern_tier": {
                "type": "choice",
                "instructions": (
                    "Is the latest user message showing that the person may "
                    "want to die or hurt themselves? Answer acute if they "
                    "state intent, a plan, means or timing, an attempt in "
                    "progress, or danger to someone else. Answer concern if "
                    "they say something indirect or passive — 'everyone would "
                    "be better off without me', 'I wish I could disappear', "
                    "'what's the point', persistent hopelessness, or past "
                    "self-harm with no current intent stated. Answer normal "
                    "otherwise. Judge only the latest user message."
                ),
                "criteria": {
                    "normal": "No sign of suicidal thoughts or self-harm.",
                    "concern": (
                        "Indirect or passive ideation, hopelessness, or past "
                        "self-harm with no current intent."
                    ),
                    "acute": (
                        "Stated intent, plan, means, timing, attempt in "
                        "progress, or danger to someone else."
                    ),
                },
            }
        }

    @staticmethod
    def register_question() -> dict[str, Any]:
        return {
            "register": {
                "type": "choice",
                "instructions": (
                    "Is the latest user message playful or serious? Answer "
                    "playful when they are joking, bantering, or teasing. "
                    "Answer serious when they are upset, hurting, or handling "
                    "something heavy. Answer neutral otherwise."
                ),
                "criteria": {
                    "playful": "Joking, bantering, or teasing.",
                    "serious": "Upset, hurting, or handling something heavy.",
                    "neutral": "Neither clearly playful nor serious.",
                },
            }
        }

    @staticmethod
    def situation_question() -> dict[str, Any]:
        return {
            "situation": {
                "type": "choice",
                "instructions": (
                    "What is happening in the latest user message? Answer "
                    "venting when they are unloading or grieving without "
                    "asking for input. Answer thinking_aloud when they are "
                    "working something out aloud. Answer asking_decision when "
                    "they ask what to do. Answer overwhelmed when they are "
                    "drowning or attacking themselves. Answer good_news when "
                    "they are sharing good news. Answer banter when they are "
                    "playing. Answer angry_at_wren when they are annoyed at "
                    "the assistant. Answer spiraling when they are panicking "
                    "or spiraling. Answer everyday_smalltalk otherwise."
                ),
                "criteria": {
                    "everyday_smalltalk": "Ordinary chat.",
                    "venting": "Unloading or grieving without asking for input.",
                    "thinking_aloud": "Working something out aloud.",
                    "asking_decision": "Asking what to do.",
                    "overwhelmed": "Drowning or attacking themselves.",
                    "good_news": "Sharing good news.",
                    "banter": "Playing around.",
                    "angry_at_wren": "Annoyed at the assistant.",
                    "spiraling": "Panicking or spiraling.",
                },
            }
        }

    @staticmethod
    def default_questions() -> dict[str, Any]:
        merged: dict[str, Any] = {}
        merged.update(DecisionModel.thread_continue_question())
        merged.update(DecisionModel.recent_context_required_question())
        merged.update(DecisionModel.is_memory_required_question())
        merged.update(DecisionModel.analyze_user_chat())
        merged.update(DecisionModel.agent_emotion())
        merged.update(DecisionModel.concern_tier_question())
        merged.update(DecisionModel.register_question())
        merged.update(DecisionModel.situation_question())
        return merged

    async def get_decisions(
        self,
        current_chat: str,
        chat_history: list[ChatTurn],
        questions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = format_turns_for_clef(chat_history, current_chat)
        payload = questions if questions is not None else self.default_questions()
        raw = await self._client.aevaluate(state=state, questions=payload)
        inject, split, memory = parse_thread_and_memory(
            raw,
            inject_threshold=self._settings.thread_inject_threshold,
            split_threshold=self._settings.thread_split_threshold,
            memory_threshold=self._settings.memory_required_threshold,
        )
        signals = parse_persona_signals(raw)
        return {
            "raw": raw,
            "inject_previous_chat": inject,
            "split_thread": split,
            "memory_required": memory,
            "persona_signals": signals,
        }
