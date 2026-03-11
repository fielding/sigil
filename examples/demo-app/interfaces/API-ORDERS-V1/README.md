---
id: API-ORDERS-V1
type: api
status: active
---

# Orders API

## Description

Handles the checkout flow: creates orders from cart contents, tracks order status, and triggers notifications. This is the most complex service because it orchestrates across catalog (price verification), cart (reading items), auth (user identity), and notifications (confirmation emails).

## Contract

### `POST /api/orders/checkout`

Creates an order from the user's current cart. Requires auth token.

Returns `201` with the new order:

```json
{
  "id": "ord-a1b2c3d4",
  "user_id": "u-001",
  "lines": [
    { "book_id": "b-001", "quantity": 2, "price_cents": 4500 }
  ],
  "total_cents": 9000,
  "status": "confirmed"
}
```

### `GET /api/orders`

Lists all orders for the authenticated user.

### `GET /api/orders/:id`

Returns a single order by ID.

## Links

- Provided by: [[COMP-order-service]]
- Consumed by: [[COMP-web-app]]
- Gates: [[GATE-0003]]
