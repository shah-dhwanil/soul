"""Application settings from environment."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_GROQ_CHAT_MODEL = "openai/gpt-oss-120b"


def _normalize_groq_model_id(model: str) -> str:
    stripped = model.strip()
    if stripped in {"gpt-oss-120b", "gpt-oss-20b"}:
        return f"openai/{stripped}"
    return stripped


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
        default=DEFAULT_GROQ_CHAT_MODEL,
        validation_alias="GROQ__AGENT_MODEL",
        alias="GROQ__AGENT_MODEL",
    )
    graphiti_llm_model: str = Field(
        default=DEFAULT_GROQ_CHAT_MODEL,
        validation_alias="GRAPHITI_LLM_MODEL",
        alias="GRAPHITI_LLM_MODEL",
    )
    cf_account_id: str = Field(validation_alias="CF_ACCOUNT_ID", alias="CF_ACCOUNT_ID")
    cf_ai_api_token: str = Field(
        validation_alias="CF_AI_API_TOKEN", alias="CF_AI_API_TOKEN"
    )
    clef_model: str = Field(default="@cf/cloudflare/clef-flash")

    decision_history_limit: int = 3
    pipeline_history_limit: int = 10
    split_generation_history_limit: int = 50
    thread_inject_threshold: float = 0.5
    thread_split_threshold: float = 0.2
    min_turns_before_split: int = 2
    memory_search_timeout_seconds: float = 8.0
    memory_num_results: int = 5
    crisis_resources: str = Field(
        default="",
        validation_alias="CRISIS_RESOURCES",
        alias="CRISIS_RESOURCES",
    )

    min_conversations_for_ingest: int = Field(default=10)
    idle_ingest_interval_minutes: int = Field(default=30)
    outbox_poll_interval_s: float = Field(default=5.0)
    outbox_max_attempts: int = Field(default=5)
    max_conversations_per_episode: int = Field(default=50)
    memory_ingest_enabled: bool = Field(default=True)
    graphiti_build_indices_on_startup: bool = Field(default=False)

    @model_validator(mode="after")
    def _normalize_models(self) -> "Settings":
        self.groq_agent_model = _normalize_groq_model_id(self.groq_agent_model)
        self.graphiti_llm_model = _normalize_groq_model_id(self.graphiti_llm_model)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
