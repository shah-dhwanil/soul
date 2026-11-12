from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agent.repositories.persona import PersonaRepository
from agent.services.memory import MemoryService
from agent.services.turns import TurnService


def get_turn_service(request: Request) -> TurnService:
    service = getattr(request.app.state, "turn_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail={"code": "service_unavailable"})
    return service


TurnServiceDep = Annotated[TurnService, Depends(get_turn_service)]


def get_current_user_id(
    x_user_id: Annotated[str | None, Header(alias="X-USER-ID")] = None,
) -> str:
    if x_user_id is None or not x_user_id.strip():
        raise HTTPException(status_code=400, detail={"code": "missing_user_id"})
    return x_user_id.strip()


CurrentUserId = Annotated[str, Depends(get_current_user_id)]


def require_matching_user(user_id: str, current_user_id: CurrentUserId) -> str:
    """Path `user_id` must equal the X-USER-ID header."""
    if user_id != current_user_id:
        raise HTTPException(status_code=400, detail={"code": "user_id_mismatch"})
    return user_id


MatchingUserId = Annotated[str, Depends(require_matching_user)]


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise HTTPException(status_code=503, detail={"code": "service_unavailable"})
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_persona_repo(session: SessionDep) -> PersonaRepository:
    return PersonaRepository(session)


PersonaRepoDep = Annotated[PersonaRepository, Depends(get_persona_repo)]


def get_memory_service(request: Request) -> MemoryService:
    service = getattr(request.app.state, "memory_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail={"code": "service_unavailable"})
    return service


MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
