# Soul API

FastAPI service that wires the [`agent`](../agent) turn pipeline, memory worker, and Graphiti ingestion.

```bash
cd apps/api
uv run uvicorn main:app --reload
```

Requires the same env vars as the agent package (`DATABASE_URL`, Groq, Clef, Graphiti, etc.) plus `JWT_SECRET` — a random secret of at least 32 bytes. The app refuses to start without it, because every `/v1` route takes its identity from a signed access token.

## Migrations

Two chains, two schemas:

- `cd apps/agent && uv run alembic upgrade head` — the `agent` schema (persona, traits, memory).
- `cd apps/api && uv run alembic upgrade head` — the `api` schema (accounts). The API owns this chain; it never touches the `agent` schema.

## Identity

Every `/v1` route reads the user from `Authorization: Bearer <access token>`. The old `X-USER-ID` header is gone (see [ADR 0005](../../docs/adr/0005-email-password-jwt-auth.md)). `POST /v1/chat` takes `{"message": "..."}`.

Auth endpoints live under `/v1/auth`: `register`, `login`, `refresh`, `me`, `complete-onboarding`.
