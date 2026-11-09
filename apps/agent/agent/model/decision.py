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
                    "Does the current chat require context from chat history to "
                    "generate a good reply — i.e. is it related to recent chats?"
                ),
            }
        }

    @staticmethod
    def is_memory_required_question() -> dict[str, Any]:
        return {
            "memory_required": {
                "type": "noul",
                "instructions": (
                    "Does the current chat require facts from long-term memory "
                    "about the user?"
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
            continue_threshold=self._settings.thread_continue_threshold,
        )
        return {
            "raw": raw,
            "inject_previous_chat": inject,
            "split_thread": split,
            "memory_required": memory,
        }
