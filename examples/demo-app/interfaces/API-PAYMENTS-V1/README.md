---
id: API-PAYMENTS-V1
type: api
status: active
---

# Payments API

## Description

Handles payment processing for confirmed orders. Wraps a third-party payment provider (Stripe in production, stub in demo) and provides a uniform interface for charging, refunding, and checking payment status.

## Contract

### `POST /api/payments/charge`

Charges a payment method for a confirmed order. Requires auth token.

Request:

```json
{
  "order_id": "ord-a1b2c3d4",
  "payment_method": "pm-tok-visa",
  "amount_cents": 9000,
  "currency": "usd"
}
```

Returns `201` with payment confirmation:

```json
{
  "id": "pay-x1y2z3",
  "order_id": "ord-a1b2c3d4",
  "amount_cents": 9000,
  "status": "succeeded"
}
```

### `POST /api/payments/refund`

Refunds a completed payment.

### `GET /api/payments/:id`

Returns a single payment by ID.

## Links

- Provided by: [[COMP-payment-gateway]]
- Consumed by: [[COMP-order-service]], [[COMP-admin-dashboard]]
- Gates: [[GATE-0005]]
