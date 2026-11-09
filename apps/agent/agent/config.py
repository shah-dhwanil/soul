"""Application settings from environment."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    database_url: str = Field(validation_alias="DATABASE_URL", alias="DATABASE_URL")
    checkpointer_database_url: str = Field(
        validation_alias="DATABASE__CHECKPOINTER_DATABASE_URL",
        alias="DATABASE__CHECKPOINTER_DATABASE_URL",
    )
    groq_api_key: str = Field(validation_alias="GROQ_API_KEY", alias="GROQ_API_KEY")
    groq_agent_model: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias="GROQ__AGENT_MODEL",
        alias="GROQ__AGENT_MODEL",
    )
    cf_account_id: str = Field(validation_alias="CF_ACCOUNT_ID", alias="CF_ACCOUNT_ID")
    cf_ai_api_token: str = Field(
        validation_alias="CF_AI_API_TOKEN", alias="CF_AI_API_TOKEN"
    )
    clef_model: str = Field(default="@cf/cloudflare/clef-flash")

    decision_history_limit: int = 3
    pipeline_history_limit: int = 10
    split_generation_history_limit: int = 50
    thread_continue_threshold: float = 0.5
    memory_search_timeout_seconds: float = 8.0
    memory_num_results: int = 5
    crisis_resources: str = Field(
        default="",
        validation_alias="CRISIS_RESOURCES",
        alias="CRISIS_RESOURCES",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
