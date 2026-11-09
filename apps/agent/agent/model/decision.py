from typing import Any

from langchain_cloudflare import CloudflareWorkersAIDecisionModel

class DecisionModel:

    @staticmethod
    def thread_continue_question() -> dict[str,Any]:
        return {
            "thread_continue":
                {"type": "noul", "instructions": "Does the current chat requires context of chat_history to effectivily generate output i.e. is the current chat releated to chats in chat history"}
        }

    @staticmethod
    def is_memory_required_question() -> dict[str,Any]:
        return {
            "memory_required":
                {"type": "noul", "instructions": "Does the current chat requires context from memory graph to effectively generate output"}
        }

    @staticmethod
    def analyze_user_chat()->dict[str,Any]:
        return {
            "user_emotion":{
                "type":"score",
                "instructions":"Analyze the current chat indicating the user's emotion",
                "criteria": []
            }
        }

    @staticmethod
    def agent_emotion()->dict[str,Any]:
        return {
            "user_emotion":{
                "type":"score",
                "instructions":"Analyze the current chat and define what should be our agent tone & emotion",
                "criteria": []
            }
        }
    
    async def get_decisions(self, current_chat: str, chat_history: list[str], questions:dict[str,Any]) -> dict[str, Any]:
        ...