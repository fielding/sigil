---
id: ADR-0004
status: accepted
---

# Synchronous checkout orchestration

## Context

The checkout flow crosses 4 service boundaries: auth, cart, catalog, and notifications. We need to decide whether this orchestration is synchronous (single request, all steps in sequence) or asynchronous (event-driven, saga pattern).

## Decision

Keep it synchronous. The checkout endpoint makes sequential calls to each service and returns the complete order in a single response.

## Alternatives

- **Saga pattern with events**: Each step publishes an event, the next service picks it up. More resilient to partial failures, but requires an event bus (Kafka, RabbitMQ) and compensating transactions. Massive overkill for a demo.
- **Async with polling**: Start checkout, return an order ID, let the client poll for completion. Adds complexity without clear benefit at demo scale.
- **Two-phase commit**: Guarantees atomicity across services. Extremely complex, and we don't even have real databases to commit to.

## Consequences

- The checkout request blocks until all steps complete. Latency is the sum of all service calls.
- If any step fails, the whole checkout fails. No partial orders.
- No need for an event bus, message queue, or distributed transaction coordinator.
- Notification failure doesn't fail the order (it's fire-and-forget with a try/except).
- Easy to understand and debug — the entire flow is visible in one function.

## Links

- For: [[SPEC-0004]]
