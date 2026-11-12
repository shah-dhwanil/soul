# Email + password authentication with JWT identity

The web client (`apps/web`, TanStack Start) makes Wren a public product, and ADR 0004's client-trusted `X-USER-ID` header is an impersonation hole the moment real users exist. We decided: accounts are email + password hashed with argon2 (no recovery, no verification in v1); a new `accounts` table maps one-to-one to the existing string `user_id`; the validated JWT is the **only** source of identity on every `/v1` route and the `X-USER-ID` header is removed; tokens travel as an access + refresh pair — a stateless refresh JWT (~30 days) in an HttpOnly cookie, no rotation table in v1.

## Considered options

- **JWT gate + client-set `X-USER-ID` identity** — rejected: any signed-in user could still read another user's persona, traits, and memory by changing one header.
- **Bearer tokens in localStorage** — rejected: XSS-readable; the web app should never hold tokens in JS.
- **Direct browser → API calls over CORS** — rejected: cross-site `SameSite=None` cookie complexity for no benefit; instead all API traffic flows through same-origin TanStack server functions, so the browser never speaks to FastAPI directly and no CORS layer is needed.
- **Rotating refresh tokens with server-side storage** — deferred: stronger revocation, but one more table + rotation logic; logout clearing the cookie is acceptable for v1.

## Consequences

- Every `/v1` route's identity dependency changes from header trust to JWT validation; path-param `user_id` matching now compares against the token subject.
- A signed-out-but-unexpired refresh token stays valid until expiry (no revocation) — acceptable for v1, revisit if abuse appears.
- The account's email never enters Wren's context; the agent only ever sees `user_id`.
