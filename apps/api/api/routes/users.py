"""User persona, settings, traits, memory, and conversation routes.

Responses speak in words: no stage number, dependency level, or raw signals.
"""

from dataclasses import asdict
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from agent.persona.constants.temperaments import TEMPERAMENTS
from agent.persona.layers import render_dials, render_stage_permissions
from agent.repositories.conversation import ConversationRepository
from agent.services.onboarding import create_first_conversation
from agent.services.persona_state import _resolve_dials
from agent.services.threads import ThreadService
from api.deps import (
    CurrentUserId,
    MatchingUserId,
    MemoryServiceDep,
    PersonaRepoDep,
    SessionDep,
)
from api.schemas import (
    ConversationCreated,
    CreateUserRequest,
    CreateUserResponse,
    LeaningOut,
    MemoryResponse,
    ResetLearnedResponse,
    SettingsPatch,
    SettingsResponse,
    TemperamentOut,
    TemperamentsResponse,
    TraitOut,
    TraitRename,
    TraitsResponse,
    UserSummary,
)

router = APIRouter(tags=["users"])

_NOT_FOUND = {"code": "user_not_found"}


def _field(row: Any, name: str, default: Any = None) -> Any:
    """Read a persona field from an ORM row or a plain mapping."""
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


async def _require_persona(repo, user_id: str):
    persona = await repo.get(user_id)
    if persona is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return persona


def _temperament(persona):
    return TEMPERAMENTS.get(_field(persona, "temperament"), TEMPERAMENTS["steady"])


def _explicit_view(settings: dict[str, Any]) -> dict[str, Any]:
    flat = {k: v for k, v in settings.items() if k != "dials"}
    flat.update(settings.get("dials") or {})
    return flat


def _settings_response(persona) -> SettingsResponse:
    settings = dict(_field(persona, "settings") or {})
    explicit_dials = settings.get("dials") or {}
    learned = dict(_field(persona, "learned_dials") or {})
    temperament = _temperament(persona)
    dials = _resolve_dials(
        temperament, _field(persona, "dials") or {}, learned, explicit_dials
    )
    effective = _explicit_view(settings)
    effective.update(asdict(dials))
    return SettingsResponse(
        explicit=_explicit_view(settings), learned=learned, effective=effective
    )


def _trait_out(t) -> TraitOut:
    landed = getattr(t, "last_landed_at", None)
    return TraitOut(
        id=t.id,
        kind=t.kind,
        label=t.label,
        status=t.status,
        last_landed=landed.isoformat() if landed else None,
    )


@router.get("/v1/onboarding/temperaments", response_model=TemperamentsResponse)
async def list_temperaments() -> TemperamentsResponse:
    return TemperamentsResponse(
        temperaments=[
            TemperamentOut(
                id=t.id,
                feels_like=t.feels_like,
                humor=t.humor,
                curiosity=t.curiosity,
                pushback=t.pushback,
                pace=t.pace,
                first_line=t.first_line,
                sample_reply=t.sample_reply,
            )
            for t in TEMPERAMENTS.values()
        ]
    )


@router.post("/v1/users", response_model=CreateUserResponse)
async def create_user(
    body: CreateUserRequest, user_id: CurrentUserId, repo: PersonaRepoDep
) -> CreateUserResponse:
    temperament = body.temperament if body.temperament in TEMPERAMENTS else "steady"
    # Idempotent: get_or_create returns the existing row for a known user.
    persona = await repo.get_or_create(
        user_id, temperament=temperament, locale=body.locale, timezone=body.timezone
    )
    return CreateUserResponse(
        user_id=user_id,
        temperament=_field(persona, "temperament"),
        locale=_field(persona, "locale"),
        timezone=_field(persona, "timezone"),
    )


@router.get("/v1/users/{user_id}", response_model=UserSummary)
async def get_user(user_id: MatchingUserId, repo: PersonaRepoDep) -> UserSummary:
    persona = await _require_persona(repo, user_id)
    temperament = _temperament(persona)
    dials = _resolve_dials(
        temperament,
        _field(persona, "dials") or {},
        _field(persona, "learned_dials") or {},
        (_field(persona, "settings") or {}).get("dials") or {},
    )
    traits = await repo.list_traits(user_id)
    leanings = await repo.list_leanings(user_id)
    return UserSummary(
        temperament=temperament.id,
        locale=_field(persona, "locale"),
        stage_permissions=render_stage_permissions(_field(persona, "stage", 1)),
        dials_words=render_dials(dials, seed=temperament),
        traits_count=sum(1 for t in traits if t.status == "active"),
        leanings=[
            LeaningOut(id=l.id, kind=l.kind, value=l.value, status=l.status)
            for l in leanings
            if l.status in ("tilt", "active")
        ],
    )


@router.get("/v1/users/{user_id}/settings", response_model=SettingsResponse)
async def get_settings_route(
    user_id: MatchingUserId, repo: PersonaRepoDep
) -> SettingsResponse:
    return _settings_response(await _require_persona(repo, user_id))


@router.patch("/v1/users/{user_id}/settings", response_model=SettingsResponse)
async def patch_settings(
    user_id: MatchingUserId, body: SettingsPatch, repo: PersonaRepoDep
) -> SettingsResponse:
    persona = await _require_persona(repo, user_id)
    settings = dict(_field(persona, "settings") or {})
    dials = dict(settings.get("dials") or {})
    for key, value in body.model_dump(exclude_unset=True).items():
        target = dials if key in ("warmth", "directness", "humor", "initiative") else settings
        if value is None:
            target.pop(key, None)
        else:
            target[key] = value
    if dials:
        settings["dials"] = dials
    else:
        settings.pop("dials", None)
    await repo.set_settings(user_id, settings)
    return _settings_response(await _require_persona(repo, user_id))


@router.post(
    "/v1/users/{user_id}/settings/reset-learned", response_model=ResetLearnedResponse
)
async def reset_learned(
    user_id: MatchingUserId, repo: PersonaRepoDep
) -> ResetLearnedResponse:
    await _require_persona(repo, user_id)
    await repo.reset_learned(user_id)
    return ResetLearnedResponse(learned={})


@router.get("/v1/users/{user_id}/traits", response_model=TraitsResponse)
async def list_traits(user_id: MatchingUserId, repo: PersonaRepoDep) -> TraitsResponse:
    traits = await repo.list_traits(user_id)
    leanings = await repo.list_leanings(user_id)
    return TraitsResponse(
        traits=[_trait_out(t) for t in traits if t.status != "retired"],
        leanings=[
            LeaningOut(id=l.id, kind=l.kind, value=l.value, status=l.status)
            for l in leanings
            if l.status != "retired"
        ],
    )


@router.patch("/v1/users/{user_id}/traits/{trait_id}", response_model=TraitOut)
async def rename_trait(
    user_id: MatchingUserId, trait_id: UUID, body: TraitRename, repo: PersonaRepoDep
) -> TraitOut:
    row = await repo.rename_trait(user_id, trait_id, body.label)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "trait_not_found"})
    return _trait_out(row)


@router.delete("/v1/users/{user_id}/traits/{trait_id}", status_code=204)
async def delete_trait(
    user_id: MatchingUserId, trait_id: UUID, repo: PersonaRepoDep
) -> Response:
    if not await repo.delete_trait(user_id, trait_id):
        raise HTTPException(status_code=404, detail={"code": "trait_not_found"})
    return Response(status_code=204)


@router.get("/v1/users/{user_id}/memory", response_model=MemoryResponse)
async def get_memory(user_id: MatchingUserId, memory: MemoryServiceDep) -> MemoryResponse:
    return MemoryResponse(facts=await memory.list_facts(user_id))


@router.delete("/v1/users/{user_id}/memory", status_code=204)
async def delete_memory(user_id: MatchingUserId, memory: MemoryServiceDep) -> Response:
    try:
        await memory.forget(user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail={"code": "memory_unavailable"}
        ) from exc
    return Response(status_code=204)


@router.post(
    "/v1/users/{user_id}/conversations", response_model=ConversationCreated
)
async def create_conversation(
    user_id: MatchingUserId, repo: PersonaRepoDep, session: SessionDep
) -> ConversationCreated:
    persona = await repo.get_or_create(user_id)
    thread = await ThreadService(session).get_or_create_active(user_id)
    conv_repo = ConversationRepository(session)
    line = await create_first_conversation(
        repo=conv_repo,
        user_id=user_id,
        temperament_id=_field(persona, "temperament"),
        thread_id=thread.id,
    )
    recent = await conv_repo.list_by_thread(thread.id, limit=1, newest_first=True)
    conversation_id = recent[-1].id
    return ConversationCreated(conversation_id=conversation_id, first_message=line)
