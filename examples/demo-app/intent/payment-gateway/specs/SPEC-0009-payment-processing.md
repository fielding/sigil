---
id: SPEC-0009
status: proposed
---

# Payment Processing

## Intent

Accept payments for confirmed orders through a pluggable payment provider. The demo uses a stub that always succeeds; production would swap in Stripe or similar. This keeps the order service from knowing anything about payment internals.

## Context

Currently the checkout flow in [[SPEC-0004]] creates orders but doesn't actually charge anyone. Adding payment processing closes the loop — orders aren't truly "confirmed" until payment succeeds.

The payment gateway is a separate component because payment logic has its own compliance requirements, error handling, and third-party dependencies. Keeping it isolated means the order service stays clean.

## Goals

- Charge a payment method when checkout completes
- Return clear success/failure status to the order service
- Support refunds for cancelled orders
- Pluggable provider interface (stub for demo, Stripe for prod)

## Non-goals

- PCI DSS compliance (demo only)
- Saved payment methods or wallets
- Multi-currency support beyond USD
- Subscription or recurring billing

## Design

The payment gateway exposes a simple REST API. The order service calls `POST /api/payments/charge` after creating the order record. If the charge fails, the order status moves to `payment_failed`.

Provider interface:

```python
class PaymentProvider:
    def charge(self, amount_cents: int, token: str) -> ChargeResult
    def refund(self, charge_id: str) -> RefundResult
```

The demo `StubProvider` always returns success after a 50ms fake delay.

## Links

- Belongs to: [[COMP-payment-gateway]]
- Depends on: [[SPEC-0004]]
- Depends on: [[COMP-order-service]]
- Consumes: [[API-AUTH-V1]]
- Provides: [[API-PAYMENTS-V1]]
- Gates: [[GATE-0005]]

## Acceptance Criteria

- [ ] Successful charge returns payment ID and `succeeded` status
- [ ] Failed charge returns `failed` status with error reason
- [ ] Refund endpoint reverses a completed charge
- [ ] Stub provider is swappable without changing calling code
