"""Account auth: register, login, refresh, me, complete-onboarding.

An account's email and password never leave this module. The agent only ever
sees the `user_id` carried in the token subject.
"""

from functools import lru_cache
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError

from api.config import get_auth_settings
from api.deps import AccountRepoDep, CurrentUserId
from api.rate_limit import (
    LOGIN_PER_ACCOUNT,
    LOGIN_PER_IP,
    REGISTER_PER_IP,
)
from api.schemas import (
    AccessTokenResponse,
    AccountResponse,
    AuthUserResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from api.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])

_INVALID_CREDENTIALS = {"code": "invalid_credentials"}


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """A hash for accounts that do not exist, so login timing does not leak
    which emails are registered."""
    return hash_password("wren-dummy-password-for-unknown-accounts")


def _client_ip(request: Request) -> str:
    """The caller's address, for the auth throttle."""
    client = request.client
    return client.host if client is not None else "unknown"


def _account_response(account: dict) -> AccountResponse:
    return AccountResponse(
        user_id=account["user_id"],
        email=account["email"],
        onboarded=account["onboarded"],
        onboarding_step=account["onboarding_step"],
    )


def _token_response(account: dict) -> AuthUserResponse:
    return AuthUserResponse(
        user_id=account["user_id"],
        email=account["email"],
        onboarded=account["onboarded"],
        onboarding_step=account["onboarding_step"],
        access_token=create_access_token(account["user_id"]),
        refresh_token=create_refresh_token(account["user_id"]),
    )


@router.post("/register", response_model=AuthUserResponse, status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    repo: AccountRepoDep,
) -> AuthUserResponse:
    response.headers["Cache-Control"] = "no-store"
    if not REGISTER_PER_IP.allow(_client_ip(request)):
        raise HTTPException(status_code=429, detail={"code": "rate_limited"})
    if await repo.get_by_email(body.email) is not None:
        raise HTTPException(status_code=409, detail={"code": "email_exists"})
    try:
        account = await repo.create(
            email=body.email,
            password_hash=hash_password(body.password),
            user_id=uuid4().hex,
        )
    except IntegrityError as exc:
        # Lost the race against a concurrent registration of the same email.
        raise HTTPException(status_code=409, detail={"code": "email_exists"}) from exc
    return _token_response(account)


@router.post("/login", response_model=AuthUserResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    repo: AccountRepoDep,
) -> AuthUserResponse:
    response.headers["Cache-Control"] = "no-store"
    if not LOGIN_PER_IP.allow(_client_ip(request)) or not LOGIN_PER_ACCOUNT.allow(
        body.email
    ):
        raise HTTPException(status_code=429, detail={"code": "rate_limited"})
    account = await repo.get_by_email(body.email)
    if account is None:
        verify_password(body.password, _dummy_hash())
        raise HTTPException(status_code=401, detail=_INVALID_CREDENTIALS)
    if not verify_password(body.password, account["password_hash"]):
        raise HTTPException(status_code=401, detail=_INVALID_CREDENTIALS)
    return _token_response(account)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    body: RefreshRequest, response: Response, repo: AccountRepoDep
) -> AccessTokenResponse:
    response.headers["Cache-Control"] = "no-store"
    user_id = decode_token(
        body.refresh_token,
        expected_type="refresh",
        settings=get_auth_settings(),
    )
    if user_id is None:
        raise HTTPException(
            status_code=401, detail={"code": "invalid_refresh_token"}
        )
    if await repo.get_by_user_id(user_id) is None:
        # The account is gone; the refresh token must not keep an identity alive.
        raise HTTPException(
            status_code=401, detail={"code": "invalid_refresh_token"}
        )
    return AccessTokenResponse(access_token=create_access_token(user_id))


@router.get("/me", response_model=AccountResponse)
async def me(user_id: CurrentUserId, repo: AccountRepoDep) -> AccountResponse:
    account = await repo.get_by_user_id(user_id)
    if account is None:
        raise HTTPException(status_code=404, detail={"code": "account_not_found"})
    return _account_response(account)


@router.post("/complete-onboarding", status_code=204)
async def complete_onboarding(
    user_id: CurrentUserId, repo: AccountRepoDep
) -> Response:
    if await repo.get_by_user_id(user_id) is None:
        raise HTTPException(status_code=404, detail={"code": "account_not_found"})
    await repo.set_onboarded(user_id)
    return Response(status_code=204)
