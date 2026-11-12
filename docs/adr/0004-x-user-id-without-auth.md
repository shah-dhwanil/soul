# `X-USER-ID` without authentication

> **Status**: superseded by [ADR 0005](./0005-email-password-jwt-auth.md) before the API was ever exposed beyond a trusted network.

Every `/v1` route takes the user identity from the `X-USER-ID` header, with no authentication, because the API is not public and character state is per-user rather than per-account. This is a known launch blocker: anyone who can reach the API can read or delete another user's persona state, traits, and memory by changing one header. Full authentication must land before the API is exposed beyond a trusted network.
