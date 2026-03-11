---
id: SPEC-0003
status: accepted
---

# Shopping Cart

## Intent

Let users collect books they want to buy before checking out. The cart is per-user, lives in memory, and acts as a staging area between browsing and ordering.

## Context

Without a cart, users would have to buy one book at a time. The cart service is intentionally simple — in-memory, no persistence across restarts. If we need durability later, we'd swap in Redis or a database behind the same API.

## Goals

- Add books to cart with quantity
- Remove individual books
- Clear entire cart (used after checkout)
- Return total item count for the cart badge in the UI

## Non-goals

- Cart persistence across server restarts
- Saved carts / wishlists
- Price calculation (that's the order service's job, using catalog prices)
- Cart merging for anonymous-to-logged-in transitions

## Design

The cart is a simple data structure: a user ID and a list of `(book_id, quantity)` pairs. Adding a book that's already in the cart increments the quantity.

Storage is a Python dict keyed by user ID. The [[API-CART-V1]] interface requires an auth token so we always know whose cart we're operating on.

The cart service calls [[API-CATALOG-V1]] only to validate that a book_id actually exists before adding it.

## Links

- Belongs to: [[COMP-cart-service]]
- Provides: [[API-CART-V1]]
- Consumes: [[API-CATALOG-V1]]
- Decided by: [[ADR-0003]]
- Depends on: [[COMP-catalog-service]]

## Acceptance Criteria

- [ ] Adding a book creates a new cart entry or increments existing quantity
- [ ] Removing a book leaves other items untouched
- [ ] Clearing the cart results in an empty items list
- [ ] Cart operations require a valid auth token
- [ ] Invalid book_ids are rejected with 400
