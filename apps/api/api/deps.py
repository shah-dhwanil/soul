from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agent.repositories.persona import PersonaRepository
from agent.services.memory import MemoryService
from agent.services.turns import TurnService
from api.config import get_auth_settings
from api.repositories import AccountRepository
from api.security import decode_token


def get_turn_service(request: Request) -> TurnService:
    service = getattr(request.app.state, "turn_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail={"code": "service_unavailable"})
    return service


TurnServiceDep = Annotated[TurnService, Depends(get_turn_service)]


def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """The caller's identity, taken only from a validated access token.

    A missing or malformed `Authorization: Bearer <token>` header is
    `missing_token`; a token that fails validation (expired, wrong secret,
    wrong type) is `invalid_token`, so a client can tell "refresh me" from
    "sign in again".
    """
    if not authorization:
        raise HTTPException(status_code=401, detail={"code": "missing_token"})
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail={"code": "missing_token"})
    user_id = decode_token(
        token.strip(), expected_type="access", settings=get_auth_settings()
    )
    if user_id is None:
        raise HTTPException(status_code=401, detail={"code": "invalid_token"})
    return user_id


CurrentUserId = Annotated[str, Depends(get_current_user_id)]


def require_matching_user(user_id: str, current_user_id: CurrentUserId) -> str:
    """Path `user_id` must equal the token subject."""
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


async def get_account_repo(session: SessionDep) -> AccountRepository:
    return AccountRepository(session)


AccountRepoDep = Annotated[AccountRepository, Depends(get_account_repo)]


def get_memory_service(request: Request) -> MemoryService:
    service = getattr(request.app.state, "memory_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail={"code": "service_unavailable"})
    return service


MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
