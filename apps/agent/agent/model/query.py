from typing import Any

from langchain_groq import ChatGroq

class QueryLLM:

    async def get_queries(self, current_chat:str, chat_history:list[str])-> list[dict[str,Any]]:
        ...

    async def generate_response(self, current_chat:str, chat_history:list[str], memories:list[dict[str,Any]])->str:
        ...