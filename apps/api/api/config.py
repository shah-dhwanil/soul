"""Auth settings for the API app.

`JWT_SECRET` is required on purpose: the app must fail fast at startup
rather than hand out identity it cannot trust.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    jwt_secret: str = Field(validation_alias="JWT_SECRET", alias="JWT_SECRET")
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()
