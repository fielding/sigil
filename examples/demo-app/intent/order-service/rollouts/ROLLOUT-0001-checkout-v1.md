---
id: ROLLOUT-0001
status: in-progress
---

# Checkout Flow v1 Rollout

## Overview

Rolling out the synchronous checkout flow described in [[SPEC-0004]]. This is the first version of the order pipeline — all services need to be deployed and healthy before we can enable checkout.

## Prerequisites

- [x] Catalog service deployed with [[API-CATALOG-V1]] operational
- [x] Auth service deployed with [[API-AUTH-V1]] operational
- [x] Cart service deployed with [[API-CART-V1]] operational
- [ ] Order service deployed with [[API-ORDERS-V1]] operational
- [ ] Notification service deployed and connected
- [ ] [[GATE-0001]] passing (catalog API compat)
- [ ] [[GATE-0002]] passing (auth security)
- [ ] [[GATE-0003]] passing (order service deps)

## Rollout Plan

### Phase 1: Backend services (current)
- Deploy order service to staging
- Run integration tests: checkout with mock cart
- Verify notification service receives events

### Phase 2: Frontend integration
- Enable checkout button in web app
- Add order confirmation page
- Add order history page

### Phase 3: Production
- Feature flag: `checkout_enabled=true` for 10% of users
- Monitor error rates and latency
- Ramp to 100% if p99 latency < 500ms and error rate < 1%

## Rollback

If checkout errors exceed 5%:
1. Set `checkout_enabled=false`
2. Cart data is preserved (no data loss)
3. Orders already placed remain in the system

## Links

- For: [[SPEC-0004]]
- Depends on: [[SPEC-0001]] [[SPEC-0002]] [[SPEC-0003]]
- Gates: [[GATE-0001]] [[GATE-0002]] [[GATE-0003]]
