---
id: ADR-0002
status: accepted
---

# Use JWT tokens instead of server-side sessions

## Context

We need authentication across multiple services. The question is whether to use stateful sessions (requiring a shared session store) or stateless tokens (requiring nothing shared).

## Decision

Use JWT-style tokens signed with HMAC-SHA256. Each service can verify tokens independently without calling back to the auth service or sharing a database.

## Alternatives

- **Server-side sessions with Redis**: More traditional, but adds a shared dependency. Every service would need Redis access or would need to call back to auth on every request. Adds latency and a single point of failure.
- **OAuth2 / OpenID Connect**: The right choice for production, but enormously complex for a 6-service demo. We'd spend more time on auth configuration than on demonstrating intent-first engineering.
- **API keys**: Simple but not user-facing. Works for service-to-service but doesn't help with user login.

## Consequences

- Services can verify tokens without network calls. Good for independence.
- Token revocation is hard — we'd need a blocklist. Acceptable for a demo with 1-hour expiry.
- The "JWT" implementation is simplified (not a real JWT library). Good enough to demonstrate the auth flow.
- Secret management is trivial (hardcoded). In production, this would be a serious security concern.

## Links

- For: [[SPEC-0002]]
