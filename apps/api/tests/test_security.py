from datetime import UTC, datetime, timedelta

import jwt

from api.config import get_auth_settings
from api.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$argon2id$")
    assert verify_password("correct horse battery staple", hashed) is True
    assert verify_password("wrong password", hashed) is False


def test_expired_token_decode_returns_none():
    settings = get_auth_settings()
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": "u1",
            "typ": "access",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    assert decode_token(expired, expected_type="access", settings=settings) is None


def test_tampered_token_rejected():
    settings = get_auth_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": "u1", "typ": "access", "iat": now, "exp": now + timedelta(minutes=15)},
        "a-different-secret-that-is-long-enough-01",
        algorithm="HS256",
    )
    assert decode_token(token, expected_type="access", settings=settings) is None


def test_access_token_is_not_a_refresh_token():
    settings = get_auth_settings()
    token = create_access_token("u1")
    assert decode_token(token, expected_type="refresh", settings=settings) is None


def test_refresh_token_roundtrip():
    settings = get_auth_settings()
    token = create_refresh_token("u1")
    assert decode_token(token, expected_type="refresh", settings=settings) == "u1"
