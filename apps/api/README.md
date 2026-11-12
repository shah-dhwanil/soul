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

### Auth contract

- **Tokens.** Access tokens last 15 minutes, refresh tokens 30 days. Both are HS256 JWTs with `sub` (the `user_id`), `typ` (`access` or `refresh`), `iat` and `exp`. The API returns both tokens in the JSON body — the web layer is responsible for moving the refresh token into its HttpOnly cookie.
- **Error bodies.** `{"code": "..."}` — `missing_token`, `invalid_token`, `invalid_credentials`, `email_exists`, `invalid_refresh_token`, `rate_limited`, `account_not_found`, `user_not_found`. A `401 invalid_token` means "the access token is expired or bad, refresh and retry"; a `401 missing_token` means "no token was sent". FastAPI's own `422` validation body is unchanged.
- **`me()`** returns `{user_id, email, onboarded, onboarding_step}` — snake_case; the web layer maps it to its own casing.
- **Throttle.** Login is limited to 10 attempts a minute per account and 20 a minute per address; registration to 10 an hour per address. The limiter is per API process, and behind a proxy the per-address limit applies to the proxy.
- **Tests.** `FakeAccountRepo` lives in [`api/repositories.py`](api/repositories.py) alongside the real repository; `FakePersonaRepo` lives in [`tests/test_users_api.py`](tests/test_users_api.py).
