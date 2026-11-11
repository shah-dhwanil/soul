from typing import Any

from langchain_cloudflare import CloudflareWorkersAIDecisionModel

from agent.config import Settings
from agent.decision_parsing import parse_thread_and_memory
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
    def default_questions() -> dict[str, Any]:
        merged: dict[str, Any] = {}
        merged.update(DecisionModel.thread_continue_question())
        merged.update(DecisionModel.recent_context_required_question())
        merged.update(DecisionModel.is_memory_required_question())
        merged.update(DecisionModel.analyze_user_chat())
        merged.update(DecisionModel.agent_emotion())
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
        return {
            "raw": raw,
            "inject_previous_chat": inject,
            "split_thread": split,
            "memory_required": memory,
        }
