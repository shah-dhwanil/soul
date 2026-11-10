from fastapi import APIRouter, BackgroundTasks, Request

from agent.api.deps import TurnServiceDep
from agent.api.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/v1/chat", response_model=ChatResponse)
async def post_chat(
    body: ChatRequest,
    turn_service: TurnServiceDep,
    background_tasks: BackgroundTasks,
    request: Request,
) -> ChatResponse:
    result = await turn_service.handle_turn(body.user_id, body.message)
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
    )
