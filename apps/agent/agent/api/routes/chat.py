from fastapi import APIRouter

from agent.api.deps import TurnServiceDep
from agent.api.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/v1/chat", response_model=ChatResponse)
async def post_chat(body: ChatRequest, turn_service: TurnServiceDep) -> ChatResponse:
    result = await turn_service.handle_turn(body.user_id, body.message)
    return ChatResponse(
        thread_id=result.thread_id,
        turn_id=result.turn_id,
        conversation_id=result.conversation_id,
        reply=result.reply,
        new_thread=result.new_thread,
        memory_degraded=result.memory_degraded,
        decisions=result.decisions,
    )
