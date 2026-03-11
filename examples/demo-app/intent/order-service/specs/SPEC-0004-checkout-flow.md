---
id: SPEC-0004
status: accepted
---

# Checkout Flow

## Intent

Turn a user's cart into a confirmed order. This is the critical path — it touches every other service and is where money changes hands (conceptually). Getting this right means prices are locked, inventory is checked, and the user gets confirmation.

## Context

The checkout flow is the most complex interaction in the app. It needs to:
1. Read the user's cart
2. Look up current prices from the catalog
3. Create an order record
4. Clear the cart
5. Send a confirmation notification

Each of these steps crosses a service boundary, so the failure modes matter.

## Goals

- Single POST endpoint that orchestrates the full checkout
- Lock prices at checkout time (not cart-add time)
- Clear the cart only after order is confirmed
- Trigger a notification on success
- Return the complete order object to the caller

## Non-goals

- Payment processing (we're treating all orders as free for the demo)
- Inventory reservation / stock decrement
- Partial orders (if any item fails, the whole checkout fails)
- Async order processing (everything is synchronous)

## Design

`POST /api/orders/checkout` does the following:

1. Verify auth token via [[API-AUTH-V1]]
2. Fetch cart via [[API-CART-V1]]
3. For each item, look up current price via [[API-CATALOG-V1]]
4. Create order with line items and totals
5. Clear cart via [[API-CART-V1]]
6. Send confirmation via notification service
7. Return order to caller

If the cart is empty, return 400. If any book isn't found in catalog, return 400. No partial success — it's all or nothing.

## Links

- Belongs to: [[COMP-order-service]]
- Provides: [[API-ORDERS-V1]]
- Consumes: [[API-CATALOG-V1]] [[API-CART-V1]] [[API-AUTH-V1]]
- Depends on: [[COMP-catalog-service]] [[COMP-cart-service]] [[COMP-auth-service]] [[COMP-notification-service]]
- Decided by: [[ADR-0004]]
- Gates: [[GATE-0003]]

## Rollout

- [[ROLLOUT-0001]]

## Acceptance Criteria

- [ ] Checkout with a non-empty cart creates an order and returns it
- [ ] Checkout with an empty cart returns 400
- [ ] Order total is calculated from current catalog prices, not stored cart prices
- [ ] Cart is empty after successful checkout
- [ ] Notification service receives order confirmation
- [ ] Order appears in GET /api/orders for that user
