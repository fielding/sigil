---
id: API-CART-V1
type: api
status: active
---

# Cart API

## Description

Manages per-user shopping carts. Carts are session-scoped and backed by in-memory storage. The web app uses this to let users add/remove books before checkout. The order service reads the cart to create orders.

## Contract

### `GET /api/cart`

Returns the current user's cart. Requires auth token.

```json
{
  "user_id": "u-001",
  "items": [
    { "book_id": "b-001", "quantity": 2 }
  ],
  "total_items": 2
}
```

### `POST /api/cart/add`

```json
{ "book_id": "b-001", "quantity": 1 }
```

### `DELETE /api/cart/:book_id`

Removes a book from the cart.

### `POST /api/cart/clear`

Empties the cart (called after successful checkout).

## Links

- Provided by: [[COMP-cart-service]]
- Consumed by: [[COMP-web-app]] [[COMP-order-service]]
