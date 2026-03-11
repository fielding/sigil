---
id: ADR-0005
status: accepted
---

# Fire-and-forget notification delivery

## Context

The order service triggers notifications after checkout. We need to decide whether notification delivery blocks the checkout response or happens best-effort in the background.

## Decision

Notifications are fire-and-forget. The order service calls the notification function, logs any errors, and continues. Checkout success doesn't depend on notification success.

## Alternatives

- **Guaranteed delivery with a queue**: Publish to a message queue, have a worker consume and retry. Guarantees delivery but adds infrastructure (queue, dead-letter handling, monitoring).
- **Synchronous with retry**: Call the notification service and retry on failure. Would make checkout slower and more fragile.
- **Outbox pattern**: Write notification intent to the database as part of the order transaction, process asynchronously. Requires a real database and a background worker.

## Consequences

- Notifications can be silently lost. Acceptable for a demo — we log the attempt.
- Checkout latency is not affected by notification speed.
- No need for queue infrastructure.
- Easy to upgrade later: swap the direct function call for a queue publish.

## Links

- For: [[SPEC-0005]]
