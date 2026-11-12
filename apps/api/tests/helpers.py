"""Helpers for minting tokens in tests."""

from datetime import UTC, datetime, timedelta

import jwt

from api.config import get_auth_settings
from api.security import create_access_token


def auth_headers(user_id: str) -> dict[str, str]:
    """Authorization header carrying a fresh access token."""
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def expired_access_token(user_id: str) -> str:
    """An access token whose `exp` is already in the past."""
    settings = get_auth_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": user_id,
            "typ": "access",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    return f"Bearer {token}"
