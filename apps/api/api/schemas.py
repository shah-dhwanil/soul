from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class ChatResponse(BaseModel):
    thread_id: UUID
    turn_id: UUID
    conversation_id: UUID | None
    reply: str
    new_thread: bool
    memory_degraded: bool
    decisions: dict[str, Any]
    mode: str | None = None
    concern_tier: str | None = None


class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temperament: str = "steady"
    locale: str = "en-US"
    timezone: str = "UTC"


class CreateUserResponse(BaseModel):
    user_id: str
    temperament: str
    locale: str
    timezone: str


class TemperamentOut(BaseModel):
    id: str
    feels_like: str
    humor: str
    curiosity: str
    pushback: str
    pace: str
    first_line: str
    sample_reply: str


class TemperamentsResponse(BaseModel):
    temperaments: list[TemperamentOut]


class LeaningOut(BaseModel):
    id: UUID
    kind: str
    value: str
    status: str


class TraitOut(BaseModel):
    id: UUID
    kind: str
    label: str
    status: str
    last_landed: str | None = None


class UserSummary(BaseModel):
    temperament: str
    locale: str
    stage_permissions: str
    dials_words: str
    traits_count: int
    leanings: list[LeaningOut]


class SettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    warmth: int | None = Field(default=None, ge=5, le=8)
    directness: int | None = Field(default=None, ge=4, le=8)
    humor: int | None = Field(default=None, ge=0, le=6)
    initiative: int | None = Field(default=None, ge=2, le=5)
    length: Literal["brief", "match", "longer"] | None = None
    advice: Literal["ask_first", "once", "direct"] | None = None
    address: str | None = Field(default=None, max_length=80)
    nickname: str | None = Field(default=None, max_length=80)
    check_ins: Literal["off", "events", "occasional"] | None = None
    emoji: Literal["never", "only_if_i_use_them"] | None = None


class SettingsResponse(BaseModel):
    explicit: dict[str, Any]
    learned: dict[str, Any]
    effective: dict[str, Any]


class ResetLearnedResponse(BaseModel):
    learned: dict[str, Any] = {}


class TraitRename(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=200)

    @field_validator("label")
    @classmethod
    def _label_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("label must not be blank")
        return value.strip()


class TraitsResponse(BaseModel):
    traits: list[TraitOut]
    leanings: list[LeaningOut]


class MemoryResponse(BaseModel):
    facts: list[str]


class ConversationCreated(BaseModel):
    conversation_id: UUID
    first_message: str


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=1024)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: Any) -> Any:
        """Emails are stored lowercase and trimmed."""
        if isinstance(value, str):
            return value.strip().lower()
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1)


class AuthUserResponse(BaseModel):
    """A signed-in account plus its token pair."""

    user_id: str
    email: str
    onboarded: bool
    onboarding_step: int
    access_token: str
    refresh_token: str


class AccountResponse(BaseModel):
    """An account without its credentials or tokens."""

    user_id: str
    email: str
    onboarded: bool
    onboarding_step: int


class AccessTokenResponse(BaseModel):
    access_token: str


class TemperamentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temperament: str = Field(min_length=1)


class TemperamentPatchResponse(BaseModel):
    temperament: str
