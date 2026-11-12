# Wren Web Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the public Wren product web app — landing, onboarding, chat, settings, and the read-only `/you` view — on TanStack Start, styled warm-pastel with GSAP motion, talking to the existing FastAPI backend exclusively through server functions.

**Architecture:** The browser never calls FastAPI directly. TanStack Start server functions (`src/server/*`) proxy every API call, attaching a Bearer access JWT from a first-party HttpOnly cookie; on `401 invalid_token` they silently refresh via the refresh-JWT cookie and retry once. Route guards read `GET /v1/auth/me` server-side in `beforeLoad`. Five surfaces share one design system; per-page deliverables are mostly independent after Task 4.

**Tech Stack:** TanStack Start (Cloudflare adapter) + TanStack Router/Query, pnpm, TypeScript strict, Tailwind v4, shadcn/ui, GSAP, Vitest.

**Spec:** Decisions captured in `docs/adr/0005-email-password-jwt-auth.md` (auth), `CONTEXT.md` (vocabulary: Temperament, Dial, Trait, Leaning, Onboarding, Account), and the Wren persona spec `docs/Wren_Companion_Persona_Spec_v2.3_MVP_No_L4.md` (brand voice and landing copy source). The API contract consumed here is defined in `apps/api` (see the backend plan: `docs/superpowers/plans/2026-11-12-wren-auth-backend.md`) — Tasks 3–5 of that plan (JWT identity, auth routes, onboarding step tracking) must land first.

## Global Constraints

- Package manager: **pnpm**; all commands run as `pnpm --dir apps/web <cmd>`; TypeScript `strict: true`.
- Tokens live **only** in first-party HttpOnly `Secure` cookies (`wren_at` access, `wren_rt` refresh); never in `localStorage`, never readable from component JS. Access TTL follows the backend (15 min), refresh 30 days.
- API base URL comes from env `WREN_API_URL` (server-side only). No `CORSMiddleware` is needed or added.
- Every server function returns a discriminated result: `{ ok: true, data } | { ok: false, code: string, status: number }` — no thrown exceptions across the boundary.
- Route set (exact): `/`, `/login`, `/onboarding`, `/chat`, `/settings`, `/you`. Protected: `/chat`, `/settings`, `/you`, `/onboarding` (signed-out → redirect `/login?next=<path>`).
- Onboarding is done iff `me().onboarded === true` (server-side flag; never a localStorage flag). Signed-in users with `onboarded === false` hitting `/chat`, `/settings`, `/you` → redirect `/onboarding`; users with `true` hitting `/onboarding` → redirect `/chat`.
- Onboarding is **The Arc** (same four facts as before, different feel — not a form wizard): clean Account auth → brief meet frame → temperament **duel tournament** (4 → 2 → 1) → story Name beat → story Dials beat (“tune this Wren”) → **opening-line reveal** (`first_line`) → `/chat`. Account stays a clean auth screen; name and dials get story chrome after the duel. Progress UI reads as story beats, not “Step 1/4”.
- Onboarding **resumes**: `me().onboardingStep` (0 = registered only, 1 = temperament chosen, 2 = name set, 3 = dials tuned, 4 = done) jumps straight to the saved beat, with every previously-completed answer pre-filled from the API (temperament via `fetchUserSummary`, name/dials via `fetchSettings`). The name beat is **required** (no skip). Changing a temperament after the persona exists calls `changeTemperament` (PATCH), never `createUser`. Backend step semantics are unchanged — UX only.
- Landing page has **no pricing, trial, or subscription copy anywhere**; all copy is in Wren's voice per the persona spec positioning: "A steady friend who pays attention, tells you the truth once, and becomes recognizably yours the longer you talk." Wren is never described as a therapist, coach, assistant, or partner.
- Chat renders only the `reply`; `mode`, `concern_tier`, `decisions` are never displayed. `memory_degraded: true` shows one subtle dismissible notice. `new_thread: true` inserts a "new conversation" divider above the reply.
- Settings dial ranges are API-enforced: warmth **5–8**, directness **4–8**, humor **0–6**, initiative **2–5**; enums exactly: `length` brief|match|longer, `advice` ask_first|once|direct, `check_ins` off|events|occasional, `emoji` never|only_if_i_use_them; `address`/`nickname` ≤ 80 chars.
- `/you` is strictly read-only (traits, leanings, memory facts; no edit/delete controls).
- Visual system: warm pastel palette (define 5 step tokens in `styles/app.css` CSS variables), soft organic shapes, generous whitespace, responsive desktop-first with mobile parity.

## Review Focus

Failure modes page tests won't cover, each pinned by a test or explicit verification in the owning task:

1. **Access cookie expired mid-session** → next server call auto-refreshes and retries once; user sees nothing (no logout flicker, no data loss). — Task 4, step 1 (`test_refreshes_once_on_401`).
2. **Refresh cookie expired/invalid** → clean redirect to `/login?next=<original path>`, form intact, no error toast loop. — Task 5, step 1 (guard test).
3. **Blank or whitespace-only chat message** → send button disabled and Enter does nothing; no request fires. — Task 8, step 1 (`test_blank_message_blocked`).
4. **User-authored strings rendered anywhere** (`address`, `nickname`, trait labels, memory facts, chat text) → React text interpolation only, never `dangerouslySetInnerHTML`; GSAP animates wrappers, not HTML injection. — Task 8, step 1 (assertion in `test_renders_reply_as_text`).
5. **`memory_degraded: true` reply** → reply still renders; single dismissible inline notice; not an error state. — Task 8, step 1 (`test_memory_degraded_shows_notice`).

---

## File Structure

```
apps/web/
├── package.json, tsconfig.json, vite.config.ts, wrangler.jsonc
├── src/
│   ├── routes/            __root.tsx, index.tsx, login.tsx, onboarding.tsx, chat.tsx, settings.tsx, you.tsx
│   ├── server/            client.ts (fetch wrapper), session.ts (cookies + refresh), auth.ts, wren.ts (server fns)
│   ├── lib/               types.ts (API shapes), motion.ts (GSAP helpers), guards.ts (beforeLoad helpers)
│   ├── components/        ui/ (shadcn), landing/, onboarding/, chat/, shared/
│   └── styles/app.css     Tailwind v4 + palette tokens
```

---

### Task 1: Scaffold `apps/web`

**Files:**
- Create: `apps/web/{package.json,tsconfig.json,vite.config.ts,src/routes/__root.tsx,src/styles/app.css}`

**Interfaces:**
- Produces: running TanStack Start app at `pnpm --dir apps/web dev`; `~/` path alias to `src/`; Tailwind v4 wired; `__root.tsx` renders a shell with a temporary placeholder index route.

- [ ] **Step 1: Scaffold** `pnpm create @tanstack/start@latest` (or manual minimal Start template) into `apps/web`; pin deps; configure `vite.config.ts` with the TanStack Start React plugin, Tailwind v4 plugin, and the `~/` alias; wire `QueryClientProvider` into `__root.tsx` (TanStack Query is the data layer for all components from Task 7 on).
- [ ] **Step 2: Verify** `pnpm --dir apps/web dev` serves the placeholder at `http://localhost:3000`, and `pnpm --dir apps/web build` passes.
- [ ] **Step 3: Commit** `git add apps/web && git commit -m "feat(web): scaffold TanStack Start app with Tailwind v4"`

---

### Task 2: Design system — palette, fonts, shadcn base

**Files:**
- Modify: `src/styles/app.css`, `src/routes/__root.tsx`
- Create: `src/components/ui/*` (shadcn CLI output: button, input, label, card, slider, select, accordion, dialog, textarea)

**Interfaces:**
- Produces: CSS variables `--wren-bg`, `--wren-surface`, `--wren-ink`, `--wren-accent`, `--wren-accent-soft` (warm pastel values chosen here once and reused everywhere); shadcn components themed from those variables; root shell with font loading and footer-less blank canvas.

- [ ] **Step 1: Define palette tokens + font stack in `app.css`; theme shadcn variables from them; add base components via `pnpm --dir apps/web dlx shadcn@latest add button input label card slider select accordion dialog textarea`.**
- [ ] **Step 2: Verify** dev server shows themed placeholder; no FOUC on reload.
- [ ] **Step 3: Commit** `feat(web): warm pastel design system and shadcn base components`

---

### Task 3: API types

**Files:**
- Create: `src/lib/types.ts`

**Interfaces:**
- Produces (exact names used by Tasks 4–10):
  - `Tokens { accessToken: string; refreshToken: string }`
  - `AuthUser { userId: string; email: string; onboarded: boolean; onboardingStep: number }`
  - `Temperament { id, feelsLike, humor, curiosity, pushback, pace, firstLine, sampleReply }`
  - `Settings { explicit: Record<string, unknown>; learned: Record<string, unknown>; effective: Record<string, unknown> }`
  - `SettingsPatch { warmth?, directness?, humor?, initiative?, length?, advice?, checkIns?, emoji?, address?, nickname? }`
  - `Trait { id, kind, label, status, lastLanded: string | null }`; `Leaning { id, kind, value, status }`; `YouView { traits: Trait[]; leanings: Leaning[]; facts: string[] }`
  - `ChatResult { threadId, turnId, reply, newThread, memoryDegraded }` (internals `mode`/`concern_tier`/`decisions` intentionally dropped at this layer)

- [ ] **Step 1: Write types mirroring the backend schema field-for-field (snake_case → camelCase mapping fixed here once).**
- [ ] **Step 2: Verify** `pnpm --dir apps/web exec tsc --noEmit` passes.
- [ ] **Step 3: Commit** `feat(web): API response types`

---

### Task 4: Server functions — fetch wrapper, session cookies, auth

**Files:**
- Create: `src/server/client.ts`, `src/server/session.ts`, `src/server/auth.ts`
- Test: `apps/web/tests/session.test.ts` (Vitest)

**Interfaces:**
- Consumes: Task 3 types; backend endpoints from the auth plan.
- Produces (server functions, exact names — Tasks 5–10 import these):
  - `register({ email, password }) → Result<AuthUser>` (sets both cookies from response tokens)
  - `login({ email, password }) → Result<AuthUser>` (sets both cookies)
  - `logout() → Result<null>` (clears both cookies)
  - `me() → Result<AuthUser | null>` (null when no/expired-and-unrefreshable session; consumes `wren_at`, silently refreshes via `wren_rt` on 401)
  - `completeOnboarding() → Result<null>`
- Produces: `callApi<T>(path, init)` in `client.ts` — attaches `Authorization: Bearer <wren_at>`, on `401 {"code":"invalid_token"}` calls `POST /v1/auth/refresh` with `wren_rt`, replaces `wren_at`, retries **once**, then surfaces `{ ok: false, ... }`.

- [ ] **Step 1: Write the failing Vitest tests** (pure logic, `fetch` mocked):

```ts
// apps/web/tests/session.test.ts — assertions to implement
test_parses_and_serializes_cookie_values()            // roundtrip of wren_at/wren_rt via cookie helpers
test_refreshes_once_on_401()                          // first call 401 invalid_token, refresh 200, retry 200 → ok; wren_at cookie replaced
test_does_not_retry_twice()                           // retry also 401 → { ok: false, code: "invalid_token" }, no second refresh call
test_me_returns_null_without_cookies()
```

- [ ] **Step 2: Run** `pnpm --dir apps/web test` → expect FAIL (modules missing).
- [ ] **Step 3: Implement** `session.ts` (cookie get/set/clear on the server-function response), `client.ts` (`callApi` with the refresh-once rule), `auth.ts` (five functions above).
- [ ] **Step 4: Run** `pnpm --dir apps/web test` → PASS (4 tests); `tsc --noEmit` clean.
- [ ] **Step 5: Commit** `feat(web): server-side session with refresh-once cookie auth`

---

### Task 5: Route guards + `/login`

**Files:**
- Create: `src/routes/login.tsx`, `src/lib/guards.ts`
- Modify: `src/routes/__root.tsx` (header nav: "Begin" when signed out / "Chat" when signed in)

**Interfaces:**
- Consumes: Task 4 `me`, `login`, `logout`.
- Produces: `requireAuth(nextPath: string)` and `redirectIfOnboarded()` in `guards.ts` — used in `beforeLoad` of protected routes (Task 6–10 wire them): no session → `/login?next=`; `onboarded === false` on `/chat|/settings|/you` → `/onboarding`; `true` on `/onboarding` → `/chat`.

- [ ] **Step 1: Write the failing test** (`apps/web/tests/guards.test.ts`): `test_guard_matrix()` — for each (path, me-result) pair asserts the exact redirect target or `undefined` (stay).
- [ ] **Step 2: Run** `pnpm --dir apps/web test` → FAIL.
- [ ] **Step 3: Implement** `guards.ts` + `login.tsx` (email + password form, calls `login`, then `next` param or `/onboarding`-per-flag redirect; shows API `code` as inline error text, same message for unknown email and wrong password).
- [ ] **Step 4: Verify against the real backend**: run `uv run --directory apps/api uvicorn main:app` with `WREN_API_URL` set; register a user via `/login` flow; confirm redirect target and cookie set (devtools). **Check Review Focus 2:** expire `wren_rt` → next protected visit lands on `/login?next=…` cleanly.
- [ ] **Step 5: Run tests** → PASS; commit `feat(web): route guards and login page`

---

### Task 6: Landing page

**Files:**
- Modify: `src/routes/index.tsx`
- Create: `src/components/landing/{Hero,WhatIs,TemperamentTeaser,Faq,ClosingCta}.tsx`

**Interfaces:**
- Consumes: Task 2 tokens/components; persona-spec copy (Global Constraints).
- Produces: GSAP scroll-reveal helper `useReveal(ref, options)` in `src/lib/motion.ts` (Tasks 7–8 reuse).

- [ ] **Step 1: Build sections** — Hero: headline "A friend who pays attention." + positioning line + "Begin" CTA; WhatIs: three quiet statements from the spec voice; TemperamentTeaser: the four cards (`steady`/`wry`/`gentle`/`tinker` with their `feels_like` lines — hardcode display text, do not fetch); FAQ: accordion, honest answers (what Wren is/isn't, privacy, memory), **no pricing**; ClosingCta + footer (privacy/terms placeholders).
- [ ] **Step 2: Motion** — `useReveal` on each section (fade + 24px rise, staggered children); hero entrance on load; `prefers-reduced-motion` respected (skip animations).
- [ ] **Step 3: Verify** dev server: scroll reveals fire once, mobile layout stacks cleanly, zero console errors.
- [ ] **Step 4: Commit** `feat(web): landing page in Wren's voice with GSAP reveals`

---

### Task 7: Onboarding — The Arc

**Files:**
- Modify: `src/routes/onboarding.tsx`
- Create: `src/components/onboarding/{StepAccount,MeetFrame,TemperamentDuel,StepName,StepDials,OpeningReveal,BeatProgress}.tsx`

**Interfaces:**
- Consumes: Task 4 `register`, `me` (for `onboardingStep`), `completeOnboarding`; `wren.ts` server functions implemented in this task: `temperaments()`, `createUser(temperamentId)` (POST — only when no persona exists yet), `changeTemperament(temperamentId)` (PATCH `/v1/users/{id}/temperament` — when resuming over an existing persona), `fetchUserSummary()`, `fetchSettings()`, `patchSettings(patch)`.
- Produces: completed account + user + settings + `onboarded = true` + `onboarding_step = 4`, then redirect `/chat`.
- Arc order (UX): Account → MeetFrame → TemperamentDuel → StepName → StepDials → OpeningReveal → `/chat`. Server step numbers stay `0→1→2→3→4` as today.

- [ ] **Step 1: Build the Arc beats**
  - **Account** — clean auth screen (email+password via `register`; not story chrome). If already signed in: "Signed in as …" + Continue.
  - **MeetFrame** — one short in-voice beat that frames the duel (no inputs); Continue into the tournament.
  - **TemperamentDuel** — load four seeds from `temperaments()`. Bracket: round 1 pairs `steady` vs `wry` and `gentle` vs `tinker` (side-by-side `sample_reply` + `feels_like`); round 2 is winners only; user keeps one each round until a single winner. On final commit: `createUser(winnerId)` if `onboardingStep < 1`, else `changeTemperament(winnerId)`. Do **not** persist mid-bracket picks — only the final winner hits the API.
  - **Name** — story beat (“What should Wren call you?”), still **required** — `patchSettings({ address })`, ≤ 80, Continue disabled while empty/whitespace.
  - **Dials** — story beat framed as “tune this Wren”; 4 sliders pre-filled from `fetchSettings().effective`, ranges per Global Constraints → `patchSettings`. Optional: pulse/update a short sample line from the winning temperament as sliders move (client-only flourish; no extra API).
  - **OpeningReveal** — show the winner’s `first_line` as the payoff; primary CTA calls `completeOnboarding()` then navigates to `/chat` (chat opener is that same `first_line`).
- [ ] **Step 2: Resume** — on mount, read `me().onboardingStep` and jump to the matching beat: `0` → Account/MeetFrame; `≥ 1` → skip the duel, load winner from `fetchUserSummary().temperament` (offer “Pick again” that re-enters TemperamentDuel and ends in `changeTemperament`); `≥ 2` pre-fill name from `settings.explicit.address`; `3` pre-fill dials from `effective`; after dials (or if returning at step 3 with dials already saved) show OpeningReveal before complete. Back-navigation is local view state only; re-submitting a completed beat is safe (idempotent POST, overwriting PATCH, monotonic server step).
- [ ] **Step 3: Motion** — GSAP: MeetFrame entrance; duel keep/swap (losing reply exits, winner holds); soft transitions between beats; OpeningReveal text reveal. `BeatProgress` shows story-beat dots/labels, never “Step N of 4”. Respect `prefers-reduced-motion` (skip animations, keep interactions).
- [ ] **Step 4: Verify against real backend**: fresh walk-through registers, completes the tournament, sets name + dials, sees OpeningReveal with `first_line`, lands on `/chat` with that line as Wren’s opening bubble; abandon after temperament (step 1), log back in, resume past the duel with winner shown; use “Pick again”, change winner, confirm persona re-seeds (new `first_line` on reveal and `/chat`).
- [ ] **Step 5: Commit** `feat(web): onboarding Arc with temperament duel and opening reveal`

---

### Task 8: Chat page

**Files:**
- Modify: `src/routes/chat.tsx`
- Create: `src/server/wren.ts` additions (`sendChat`, `startConversation`, `fetchYou`), `src/components/chat/{MessageList,Composer,TypingIndicator,Notice}.tsx`

**Interfaces:**
- Consumes: Task 4 session; Task 7's `wren.ts` functions (including `fetchUserSummary()` for the temperament id); new in this task: `sendChat(message: string) → Result<ChatResult>`, `startConversation() → Result<{ conversationId: string; firstMessage: string }>`, `fetchYou() → Result<YouView>` (used by Task 9).
- Produces: chat transcript state.

- [ ] **Step 1: Write the failing Vitest tests** (`apps/web/tests/chat.test.ts`) for the reducer/formatting logic only:

```ts
// apps/web/tests/chat.test.ts — assertions to implement
test_blank_message_blocked()               // "   " → send disabled, no sendChat call
test_new_thread_inserts_divider()          // ChatResult.newThread → divider element above reply
test_memory_degraded_shows_notice()        // ChatResult.memoryDegraded → single dismissible Notice, reply still renders
test_renders_reply_as_text()               // reply with <img src=x onerror=alert(1)> renders as text, zero DOM injection
```

- [ ] **Step 2: Run** `pnpm --dir apps/web test` → FAIL.
- [ ] **Step 3: Build the page** — single centered column; opener bubble is the temperament's `first_line` (match `fetchUserSummary().temperament` against `temperaments()`); composer with Enter-to-send; pending state = `TypingIndicator`; on reply, GSAP text reveal (typewriter-ish opacity/clip on the bubble, per Global Constraints no internal fields); `new_thread` divider; "New conversation" button → `startConversation()` and render its `firstMessage` as Wren's bubble; error `code` → inline retry message.
- [ ] **Step 4: Verify** — live conversation with the backend: replies reveal animated, divider appears on thread rollover, `memory_degraded` path shows the notice once (Review Focus 5), XSS assertion passes (Review Focus 4).
- [ ] **Step 5: Run tests** → PASS; commit `feat(web): chat page with animated replies`

---

### Task 9: Settings page

**Files:**
- Modify: `src/routes/settings.tsx`
- Create: `src/components/settings/{DialSlider,PreferenceSelect,NameFields}.tsx`

**Interfaces:**
- Consumes: Task 7's `fetchSettings`/`patchSettings`; `resetLearned()` (add to `wren.ts`: `POST /v1/users/{id}/settings/reset-learned`).

- [ ] **Step 1: Build** — dials as 4 sliders with exact ranges and a "temperament default" hint from `effective`; selects for length/advice/check-ins/emoji with the exact enum options; name fields (`address`, `nickname`, ≤ 80, char counter); "Reset what Wren learned" button with confirm `Dialog` → `resetLearned()`. Save on change (debounced `patchSettings`), optimistic UI with rollback on error.
- [ ] **Step 2: Verify** — change warmth → refetch shows new `explicit` value; range violations impossible from UI; reset empties `learned`.
- [ ] **Step 3: Commit** `feat(web): settings page with dials, preferences, and name`

---

### Task 10: `/you` — read-only view

**Files:**
- Modify: `src/routes/you.tsx`
- Create: `src/components/you/{TraitList,LeaningList,FactList}.tsx`

**Interfaces:**
- Consumes: Task 8's `fetchYou()`.

- [ ] **Step 1: Build** — framed as "How Wren sees you today": traits (label, kind, `last_landed`), leanings (kind/value), memory facts as plain list; empty states ("Wren hasn't learned this about you yet"); strictly no mutation controls (Global Constraints). GSAP reveal on list items.
- [ ] **Step 2: Verify** — renders live data from an onboarded user; empty account shows empty states.
- [ ] **Step 3: Commit** `feat(web): read-only /you view of traits, leanings, and memory`

---

### Task 11: Cloudflare deployment

**Files:**
- Create: `apps/web/wrangler.jsonc`
- Modify: `apps/web/vite.config.ts`, `apps/web/package.json` (deploy scripts), root `.gitignore` (`.wrangler/`)

**Interfaces:**
- Consumes: everything above; env `WREN_API_URL` configured as a Cloudflare secret/variable.

- [ ] **Step 1: Configure** the TanStack Start Cloudflare target + `wrangler.jsonc` (name `wren-web`, env var `WREN_API_URL` non-secret placeholder, real value set via `wrangler secret put`).
- [ ] **Step 2: Verify** `pnpm --dir apps/web build` produces the Worker bundle and `wrangler dev` serves the landing page with server functions working (login roundtrip against a reachable API).
- [ ] **Step 3: Commit** `feat(web): Cloudflare Workers deployment config`
