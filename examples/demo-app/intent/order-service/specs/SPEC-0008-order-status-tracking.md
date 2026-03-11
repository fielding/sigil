---
id: SPEC-0008
status: proposed
---

# Order Status Tracking

## Intent

Let users and internal systems track an order through its lifecycle: pending, confirmed, shipped, delivered, cancelled. Right now orders are created and that's it — there's no state machine.

## Context

[[SPEC-0004]] handles checkout but leaves orders in a permanent "pending" state. For a real system, we need status transitions so the UI can show "your order shipped" and internal tools can manage fulfillment.

## Goals

- Define a clear order status state machine
- Add a PATCH endpoint to advance order status
- Validate transitions (can't go from "delivered" back to "pending")
- Include timestamps for each transition

## Non-goals

- Webhook notifications on status change (notification service handles that separately)
- Shipping carrier integration
- Return/refund flow

## Design

Status transitions:
```
pending -> confirmed -> shipped -> delivered
pending -> cancelled
confirmed -> cancelled
```

New endpoint: `PATCH /api/orders/:id/status` with `{ "status": "confirmed" }`.

Invalid transitions return 409 Conflict with a message explaining what transitions are allowed from the current state.

Each order gets a `status_history` array: `[{ "status": "pending", "at": "..." }, ...]`

## Links

- Belongs to: [[COMP-order-service]]
- Provides: [[API-ORDERS-V1]]
- Depends on: [[SPEC-0004]]

## Acceptance Criteria

- [ ] Orders start in "pending" status
- [ ] Valid transitions update the status and append to history
- [ ] Invalid transitions return 409 with allowed transitions
- [ ] Status history includes timestamps
- [ ] GET /api/orders/:id includes status_history in response
