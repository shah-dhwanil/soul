"""Password hashing and JWT primitives.

Credentials never leave this module: routes pass a plaintext password in and
get a hash back. The agent never sees an email, a password, or a token — only
the `user_id` carried in the token subject.
"""

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from api.config import AuthSettings, get_auth_settings

ALGORITHM = "HS256"

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """argon2id hash of the password."""
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """True only when the password matches the stored hash."""
    try:
        return _hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError, ValueError):
        return False


def _encode(
    user_id: str, token_type: str, ttl: timedelta, settings: AuthSettings
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "typ": token_type,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_access_token(
    user_id: str, *, settings: AuthSettings | None = None
) -> str:
    """Short-lived access token (15 minutes by default)."""
    settings = settings or get_auth_settings()
    return _encode(
        user_id,
        "access",
        timedelta(minutes=settings.access_token_ttl_minutes),
        settings,
    )


def create_refresh_token(
    user_id: str, *, settings: AuthSettings | None = None
) -> str:
    """Long-lived refresh token (30 days by default)."""
    settings = settings or get_auth_settings()
    return _encode(
        user_id,
        "refresh",
        timedelta(days=settings.refresh_token_ttl_days),
        settings,
    )


def decode_token(
    token: str, *, expected_type: str, settings: AuthSettings
) -> str | None:
    """The token's subject, or None if the token is not usable.

    None covers every failure: bad signature, expired, wrong `typ`, missing
    claims, malformed token. Callers must treat None as "no identity".
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "typ"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != expected_type:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
