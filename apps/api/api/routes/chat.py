from fastapi import APIRouter, BackgroundTasks, Request

from api.deps import CurrentUserId, get_turn_service
from api.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/v1/chat", response_model=ChatResponse)
async def post_chat(
    body: ChatRequest,
    user_id: CurrentUserId,
    background_tasks: BackgroundTasks,
    request: Request,
) -> ChatResponse:
    # Resolved in the handler so body validation (422) runs before any service lookup.
    turn_service = get_turn_service(request)
    result = await turn_service.handle_turn(user_id, body.message)
    worker = getattr(request.app.state, "memory_worker", None)
    if worker is not None:
        background_tasks.add_task(worker.drain_once)
    return ChatResponse(
        thread_id=result.thread_id,
        turn_id=result.turn_id,
        conversation_id=result.conversation_id,
        reply=result.reply,
        new_thread=result.new_thread,
        memory_degraded=result.memory_degraded,
        decisions=result.decisions,
        mode=result.mode,
        concern_tier=result.concern_tier,
    )
