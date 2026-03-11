---
id: ADR-0003
status: accepted
---

# Session-scoped in-memory carts

## Context

Carts need to be per-user and available across requests within a session. We could persist them to a database or keep them in memory.

## Decision

Store carts in a Python dict keyed by user ID. Carts exist only as long as the server process is running.

## Alternatives

- **Redis**: The standard choice for session data. Fast, persistent enough, supports TTL. But adds infrastructure for a demo app.
- **Database**: Durable but slow for the frequent read-modify-write pattern of cart operations. Also requires schema/migration setup.
- **Client-side storage (localStorage)**: No server state, but then the cart API can't be used by the order service during checkout.

## Consequences

- Carts disappear on restart. Acceptable for a demo.
- No TTL or cleanup — abandoned carts grow forever during a session. Fine for demo scale.
- The cart API contract is identical regardless of backing store, so swapping to Redis later is straightforward.
- Cart operations are O(1) for lookup, O(n) for the item list where n is number of distinct books (trivially small).

## Links

- For: [[SPEC-0003]]
