# Wren Auth Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace header-trust identity with real email + password authentication (argon2, JWT) so the API is safe to expose to the public web client.

**Architecture:** A new `accounts` table (email, argon2 hash, generated `user_id`, `onboarded` flag, `onboarding_step` resume pointer) joins 1:1 to the existing string `user_id` every agent table already keys on. **The API owns this model**: it lives under `apps/api` with its own Alembic migration chain writing to a separate `api` Postgres schema — the agent schema and `apps/agent` code are untouched by auth. `api.deps.get_current_user_id` — the single identity seam — switches from reading `X-USER-ID` to decoding a Bearer access JWT. Auth endpoints live in a new `auth` router; they are repository-backed so tests keep using the codebase's fake-repo + `dependency_overrides` pattern.

**Tech Stack:** FastAPI, PyJWT (HS256), argon2-cffi, SQLAlchemy/Alembic (existing), pytest + TestClient (existing).

**Spec:** `docs/adr/0005-email-password-jwt-auth.md` (decision + rejected options); vocabulary in `CONTEXT.md` (**Account**, **Onboarding**). Exact values below in Global Constraints; nothing is left open.

## Global Constraints

- Identity comes **only** from a validated Bearer JWT. The `X-USER-ID` header is removed from every route path; requests with only that header get `401 {"code": "missing_token"}`.
- Hashing: argon2id via `argon2-cffi`'s `PasswordHasher`. No bcrypt, no sha256 for credentials.
- JWTs: HS256, secret from env `JWT_SECRET` (required; app must fail fast at startup if unset). Access token TTL **15 minutes** (`typ="access"`), refresh token TTL **30 days** (`typ="refresh"`). Claims: `sub` (user_id), `typ`, `iat`, `exp`.
- Endpoints (exact paths and status codes):
  - `POST /v1/auth/register` `{email, password}` → `201 {user_id, email, onboarded, onboarding_step, access_token, refresh_token}`; duplicate email → `409 {"code": "email_exists"}`.
  - `POST /v1/auth/login` → `200` same shape; bad credentials → `401 {"code": "invalid_credentials"}` (same body for unknown email and wrong password).
  - `POST /v1/auth/refresh` `{refresh_token}` → `200 {access_token}`; missing/expired/wrong-typ token → `401 {"code": "invalid_refresh_token"}`.
  - `GET /v1/auth/me` → `200 {user_id, email, onboarded, onboarding_step}`; requires access token.
  - `POST /v1/auth/complete-onboarding` → `204`; requires access token; sets `onboarded = true` and `onboarding_step = 4` (idempotent).
  - `PATCH /v1/users/{user_id}/temperament` `{temperament}` → `200 {temperament}`; requires access token; re-seeds the persona with the new temperament and resets explicit dial values to that temperament's defaults; allowed any time; unknown temperament id → `422`.
- `user_id` is `uuid4().hex` generated at registration; email is stored lowercase + trimmed; password minimum length **8**; email validated by Pydantic `EmailStr`.
- `onboarded` defaults to `False`; `onboarding_step` is an int (default `0`) with the exact resume semantics: `0` = registered only, `1` = temperament chosen (persona user exists), `2` = name set, `3` = dials tuned, `4` = done. Each onboarding advance sets it server-side; register/login/me always return the current value. `POST /v1/users` (temperament step) still lives in `users.py` and is unaffected except that completing it advances the step.
- Error bodies use the codebase style: `HTTPException(status, detail={"code": "..."})`.
- Email/credentials never appear in any agent prompt or memory path; the agent only ever sees `user_id`.

## Review Focus

Failure modes the route tests above don't cover, each pinned by a test in the owning task:

1. **Token signed with a different secret** must yield `401 invalid_token`, never a 500 or an identity. — Task 3, step 1 (`test_tampered_token_rejected`).
2. **Access token submitted to `/v1/auth/refresh`** must be rejected (`typ` check), not accepted. — Task 2, step 1 (`test_access_token_is_not_a_refresh_token`).
3. **Registering an email that differs only by case or surrounding spaces** from an existing one must hit the unique constraint path → `409 email_exists`. — Task 4, step 1 (`test_register_normalizes_email`).
4. **Request with only `X-USER-ID`** (the old contract) must get `401`, proving the header is dead. — Task 3, step 1 (`test_x_user_id_header_alone_is_rejected`).
5. **Expired access token** must yield `401 invalid_token` (not `missing_token`), so clients can distinguish refreshable from hard logout. — Task 2, step 1 (`test_expired_token_decode_returns_none`).

---

### Task 1: `accounts` model, migration, and repository

**Files:**
- Create: `apps/api/api/models.py` (the `Account` model — API-owned)
- Create: `apps/api/migrations/{alembic.ini,env.py,versions/<auto>_add_accounts.py}` (new Alembic chain for the API app, targeting the `api` schema only)
- Create: `apps/api/api/repositories.py`
- Test: `apps/api/tests/test_account_repository.py`

**Interfaces:**
- Produces: `AccountRepository(session)` with `async def get_by_email(self, email: str) -> dict | None`, `async def get_by_user_id(self, user_id: str) -> dict | None`, `async def create(self, *, email: str, password_hash: str, user_id: str) -> dict`, `async def set_onboarded(self, user_id: str) -> None` — all returning plain dicts (row shape: `user_id, email, password_hash, onboarded, created_at`), matching the `FakePersonaRepo` style.
- Produces: `Account` SQLAlchemy model: `user_id: Mapped[str]` primary key (String, matching the persona tables' key type), `email: Mapped[str]` unique + indexed, `password_hash: Mapped[str]`, `onboarded: Mapped[bool]` default `False`, `onboarding_step: Mapped[int]` default `0`, `created_at: Mapped[datetime]` — in the new **`api` schema**, leaving the agent schema untouched.

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_account_repository.py
import asyncio

from api.api.repositories import FakeAccountRepo  # created alongside AccountRepository for test overrides


def test_account_repo_roundtrip():
    async def run():
        repo = FakeAccountRepo()
        await repo.create(email="a@b.co", password_hash="h", user_id="u1")
        assert (await repo.get_by_email("a@b.co"))["user_id"] == "u1"
        await repo.set_onboarded("u1")
        assert (await repo.get_by_user_id("u1"))["onboarded"] is True
        assert await repo.get_by_email("missing@b.co") is None

    asyncio.run(run())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --directory apps/api pytest tests/test_account_repository.py -v`
Expected: FAIL with "No module named api.api.repositories"

- [ ] **Step 3: Implement `Account` model + `AccountRepository` + the API Alembic chain**

Create `apps/api/api/models.py` with the `Account` model (table `accounts`, `schema="api"`). Set up `apps/api/migrations/` (alembic.ini + env.py) reusing the existing database URL from `agent.config.get_settings()`, with metadata targeting **only** the API models so autogenerate never touches agent tables. Implement `AccountRepository(session)` in `apps/api/api/repositories.py` with the exact methods above (SQLAlchemy selects/inserts on `api.accounts`).

- [ ] **Step 4: Generate and apply the migration**

Run: `uv run --directory apps/api alembic revision --autogenerate -m "add accounts" && uv run --directory apps/api alembic upgrade head`
Expected: migration applies cleanly; `api.accounts` table exists with unique email; `agent` schema diff is empty.

- [ ] **Step 5: Run tests, then commit**

Run: `uv run --directory apps/api pytest -v` → PASS

```bash
git add apps/api/api/models.py apps/api/api/repositories.py apps/api/migrations/ apps/api/tests/test_account_repository.py
git commit -m "feat(api): api-owned accounts table and repository for email+password auth"
```

---

### Task 2: Security primitives (argon2 + JWT)

**Files:**
- Create: `apps/api/api/config.py`
- Create: `apps/api/api/security.py`
- Modify: `apps/api/pyproject.toml` (add `pyjwt`, `argon2-cffi`)
- Test: `apps/api/tests/test_security.py`

**Interfaces:**
- Produces: `AuthSettings(BaseSettings)` in `config.py` with fields `jwt_secret: str` (env `JWT_SECRET`), `access_token_ttl_minutes: int = 15`, `refresh_token_ttl_days: int = 30`.
- Produces (all in `security.py`, used by Tasks 3 and 4):
  - `hash_password(password: str) -> str`
  - `verify_password(password: str, hashed: str) -> bool` (argon2 verify exception → `False`)
  - `create_access_token(user_id: str) -> str` / `create_refresh_token(user_id: str) -> str`
  - `decode_token(token: str, *, expected_type: str, settings: AuthSettings) -> str | None` — returns `sub` claim or `None` on any failure (bad signature, expired, wrong `typ`).

- [ ] **Step 1: Write the failing tests**

```python
# apps/api/tests/test_security.py — assertions to implement
def test_password_hash_roundtrip():            # hash_password/verify_password agree; wrong password → False
def test_expired_token_decode_returns_none():  # craft token with exp in past → decode_token returns None
def test_tampered_token_rejected():            # token signed with different secret → None
def test_access_token_is_not_a_refresh_token():# create_access_token decoded with expected_type="refresh" → None
def test_refresh_token_roundtrip():            # create_refresh_token decoded with expected_type="refresh" → user_id
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --directory apps/api pytest tests/test_security.py -v`
Expected: FAIL with "No module named api.security"

- [ ] **Step 3: Implement `config.py` and `security.py`**

`PasswordHasher` from `argon2-cffi` for hashing; `jwt.encode/decode` (PyJWT, HS256) with claims `sub`, `typ`, `iat`, `exp` per Global Constraints. Fixture env: tests set `JWT_SECRET="test-secret"` (monkeypatch or env fixture).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --directory apps/api pytest tests/test_security.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/api/api/config.py apps/api/api/security.py apps/api/pyproject.toml apps/api/tests/test_security.py uv.lock
git commit -m "feat(api): argon2 password hashing and JWT token primitives"
```

---

### Task 3: Switch identity to JWT across all `/v1` routes

**Files:**
- Modify: `apps/api/api/deps.py:22-30` (`get_current_user_id` / `CurrentUserId`)
- Modify: `apps/api/tests/test_users_api.py`, `apps/api/tests/test_chat_api.py` (fixtures mint tokens via a test helper)
- Test: same files

**Interfaces:**
- Consumes: Task 2 `decode_token(token, expected_type="access", settings)` and `create_access_token(user_id)` for test setup (no auth routes exist yet — tests mint tokens directly).
- Produces: `get_current_user_id(authorization: str | None = Header()) -> str` — parses `Bearer <token>`, decodes with `expected_type="access"`; `401 {"code": "missing_token"}` when absent/malformed, `401 {"code": "invalid_token"}` when expired/bad signature/wrong typ. `MatchingUserId` keeps its exact semantics (path `user_id` must equal token subject) but compares against the JWT identity. This switched `CurrentUserId` is what Task 4's `me`/`complete-onboarding` and Task 5's routes consume.

- [ ] **Step 1: Write the failing tests (update existing ones)**

```python
# additions to test_users_api.py — assertions to implement
def test_missing_bearer_token_gets_401(client)      # no Authorization → 401 {"code": "missing_token"}
def test_x_user_id_header_alone_is_rejected(client) # X-USER-ID: "someone", no Bearer → 401 (old contract dead)
def test_expired_access_token_gets_invalid_token(client)  # past-exp access token → 401 {"code": "invalid_token"}
# test_chat_api.py: every existing test's X-USER-ID header setup replaced with a Bearer token minted via
# create_access_token(user_id) using the test JWT_SECRET
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --directory apps/api pytest tests/test_users_api.py tests/test_chat_api.py -v`
Expected: existing header-authed tests FAIL (401), new tests FAIL

- [ ] **Step 3: Implement the new `get_current_user_id`**

Only `deps.py` changes — routes already consume `CurrentUserId`, so no route edits. Keep `require_matching_user` logic; update its docstring to say "token subject".

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `uv run --directory apps/api pytest -v`
Expected: PASS (all files, including Task 1 and 2 tests)

- [ ] **Step 5: Update the auth ADR cross-references and commit**

`apps/agent/README.md` says "no authentication (see ADR 0004)" — update that sentence to reference ADR 0005.

```bash
git add apps/api/api/deps.py apps/api/tests/ apps/agent/README.md
git commit -m "feat(api)!: identity from Bearer JWT, X-USER-ID removed (supersedes ADR 0004)"
```

---

### Task 4: Auth routes

**Files:**
- Create: `apps/api/api/routes/auth.py`
- Modify: `apps/api/api/schemas.py` (`RegisterRequest`, `LoginRequest`, `RefreshRequest`, `AuthUserResponse`, `AccessTokenResponse`)
- Modify: `apps/api/main.py` (register the auth router alongside the existing ones)
- Test: `apps/api/tests/test_auth_api.py`

**Interfaces:**
- Consumes: Task 1 `AccountRepository` (via new dep `get_account_repo(session: SessionDep) -> AccountRepository` in `api/repositories.py`, overridable like `get_persona_repo`); Task 2 security functions; Task 3's switched `CurrentUserId` (for `me` / `complete-onboarding`).
- Produces: routes per Global Constraints, exact paths/bodies/codes. Registration generates `user_id = uuid4().hex`, lowercases+strips email, returns both tokens.

- [ ] **Step 1: Write the failing tests**

```python
# apps/api/tests/test_auth_api.py — TestClient tests with FakeAccountRepo override (Task 1) and JWT_SECRET env
def test_register_creates_account_and_returns_tokens(client)          # 201; body has user_id/email/onboarded=False/onboarding_step=0/access_token/refresh_token
def test_register_rejects_short_password(client)                      # password "short" → 422
def test_register_normalizes_email(client)                            # " A@B.co " then "a@b.co" → 409 {"code": "email_exists"}
def test_login_returns_tokens_for_valid_credentials(client)           # register then login → 200, tokens present
def test_login_same_error_for_unknown_email_and_wrong_password(client)# both → 401 {"code": "invalid_credentials"}
def test_refresh_returns_new_access_token(client)                     # register → refresh with refresh_token → 200 {access_token}
def test_refresh_rejects_access_token(client)                         # pass access_token → 401 {"code": "invalid_refresh_token"}
def test_me_returns_account(client)                                   # Bearer access → 200 {user_id, email, onboarded: False, onboarding_step: 0}
def test_complete_onboarding_sets_flag_and_step(client)               # POST → 204; GET me → onboarded True, onboarding_step 4; idempotent
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --directory apps/api pytest tests/test_auth_api.py -v`
Expected: FAIL (404 on auth routes)

- [ ] **Step 3: Implement the auth router**

Five endpoints per Global Constraints; register/login issue both tokens via Task 2 and return the account's current `onboarding_step`; `me`/`complete-onboarding` take `CurrentUserId` and look the account up by `user_id` (complete-onboarding sets `onboarded = True` and `onboarding_step = 4`). Wire router into `main.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --directory apps/api pytest tests/test_auth_api.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/api/api/routes/auth.py apps/api/api/schemas.py apps/api/api/repositories.py apps/api/main.py apps/api/tests/test_auth_api.py
git commit -m "feat(api): register/login/refresh/me/complete-onboarding routes"
```

---

### Task 5: Onboarding step advancement + temperament re-pick

**Files:**
- Modify: `apps/api/api/repositories.py` (add `advance_onboarding_step`)
- Modify: `apps/api/api/routes/users.py` (advance steps on `POST /v1/users` and `PATCH /settings`; new temperament route)
- Modify: `apps/agent/agent/repositories/persona.py` (add `reseed` — additive, agent schema unchanged)
- Test: `apps/api/tests/test_users_api.py` (additions)

**Interfaces:**
- Consumes: Task 1 `AccountRepository`; Task 3's `CurrentUserId`/`MatchingUserId`; `PersonaRepository` and `TEMPERAMENTS`.
- Produces: `AccountRepository.advance_onboarding_step(user_id: str, step: int) -> None` — monotonic: sets the stored step to `max(current, step)` so re-running onboarding actions after completion can't lower it.
- Produces: `PersonaRepository.reseed(user_id: str, temperament: str) -> dict` — updates `user_persona.temperament` and replaces the row's explicit dials with the new temperament's `default_dials`, returns the updated row.
- Produces: `PATCH /v1/users/{user_id}/temperament {temperament}` → `200 {temperament}` per Global Constraints.
- Behavior: `POST /v1/users` success → advance to ≥ `1`; `PATCH /settings` containing a non-null `address` → ≥ `2`; `PATCH /settings` containing any dial key → ≥ `3`; `complete-onboarding` (Task 4) → `4`.

- [ ] **Step 1: Write the failing tests (append to test_users_api.py)**

```python
def test_temperament_patch_reseeds_persona(client)       # create "wry" user → PATCH "steady" → persona temperament "steady", explicit dials replaced by steady defaults
def test_temperament_patch_rejects_unknown_id(client)    # PATCH "chaotic" → 422
def test_post_users_advances_onboarding_step(client)     # fresh account step 0 → POST /v1/users → me shows onboarding_step >= 1
def test_settings_patch_advances_step_for_name_and_dials(client)  # PATCH {"address": "Sam"} → step >= 2; PATCH {"warmth": 7} → step >= 3
```

(The `FakePersonaRepo` gains the `reseed` method mirroring the real one's contract.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --directory apps/api pytest tests/test_users_api.py -v`
Expected: FAIL (no PATCH route, no reseed, no step advancement)

- [ ] **Step 3: Implement**

Add the monotonic advance to `AccountRepository`; call it from the existing `users.py` route handlers; add the temperament PATCH route using `MatchingUserId` + `PersonaRepoDep.reseed`; validate the id against `TEMPERAMENTS` (422 otherwise). Add `reseed` to `PersonaRepository` and `FakePersonaRepo`.

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `uv run --directory apps/api pytest -v`
Expected: PASS (all files)

- [ ] **Step 5: Commit**

```bash
git add apps/api/api/repositories.py apps/api/api/routes/users.py apps/agent/agent/repositories/persona.py apps/api/tests/test_users_api.py
git commit -m "feat(api): onboarding step tracking and temperament re-seed"
```
