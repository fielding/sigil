# Before & After: What Sigil Adds to a Codebase

This is the same project — a small bookstore called Shelf — shown two ways. First without Sigil, then with it. The difference is what you can *ask* and *enforce*.

---

## Before Sigil

You clone the repo. Here's what you see:

```
services/
  auth/auth.py
  cart/cart.py
  catalog/routes.py
  notifications/notify.py
  orders/orders.py
app/
  layout.tsx
  page.tsx
```

197 lines of Python across 5 services. Straightforward enough. But now try to answer these questions:

**"Why does `routes.py` exist?"**
You read the code. It serves books from an in-memory dict. But *why* an in-memory dict? Was Postgres considered? Is this temporary? Who decided this?

→ No answer in the code.

**"What happens if I change the catalog API?"**
`routes.py` exports `list_books`, `get_book`, and `search_books`. Does anything else call these? Does the order service depend on the price format? What breaks?

→ You grep. Maybe you find callers. Maybe you miss one. You have no confidence.

**"Is the auth service secure?"**
`auth.py` hashes passwords. Does it ever return plaintext? Is there a policy about this? What would catch a regression?

→ You'd need to read every line and hope future changes don't slip through.

**"Can I add a dependency from orders to a new analytics service?"**
Nothing stops you. Nothing tells you this violates an architectural decision. You add it, ship it, and six months later someone wonders why the order service is coupled to 12 things.

→ No guardrails.

**"What's the blast radius of changing the order service?"**
The order service calls auth, cart, catalog, and notifications. But what calls the order service? What specs govern it? What gates protect it?

→ You'd have to map the entire system in your head.

The code is simple. The *context* is invisible.

---

## After Sigil

Same app. Same 197 lines of Python. But now there's an intent layer — 36 files (components, specs, ADRs, interfaces, gates) that answer every question above.

### "Why does `routes.py` exist?"

```
$ sigil why services/catalog/routes.py

Owned by: Catalog Service (COMP-catalog-service)

What is being built:
  [accepted] SPEC-0001: Book Catalog API
    | Provide a read-only API for browsing and searching the book inventory.
    | This is the foundational data service — everything else depends on it.
  [proposed] SPEC-0007: Catalog Search Improvements
    | Upgrade search from basic substring matching to fuzzy matching.

Why it was built this way:
  [accepted] ADR-0001: Use in-memory store for the book catalog
    | Options: Postgres, SQLite, in-memory dict.
    | Decision: In-memory dict. This is a demo app, not a production bookstore.

What enforces it:
  GATE-0001: Required endpoints must exist, prices must be integer cents
```

One command. Full chain: ownership → intent → decisions → enforcement.

### "What happens if I change the catalog API?"

```
$ sigil impact COMP-order-service

Direct (7 nodes)
  ← SPEC-0004: Checkout Flow
  ← SPEC-0008: Order Status Tracking
  → GATE-0003: Dependency policy — only allowed deps are catalog, cart, auth, notification

Secondary (18 nodes)
  → COMP-auth-service, COMP-cart-service, COMP-catalog-service, COMP-notification-service
  → API-CATALOG-V1, API-ORDERS-V1, API-AUTH-V1, API-CART-V1
  → GATE-0001, GATE-0002, GATE-0005

Blast radius: 32 nodes
```

The order service touches 32 of 36 nodes in the graph. You see this *before* you make the change, not after.

### "Is the auth service secure?"

```
$ sigil check

GATE-0001: Catalog API Compatibility         PASS
GATE-0002: Auth Security                     PASS  ← enforces password hashing, no plaintext
GATE-0003: Order Dependency Policy            PASS
GATE-0004: Spec Quality                       PASS
GATE-0005: Payment PCI Compliance             PASS  ← no raw card numbers in payment code

Gates: 5 passed, 0 failed
```

GATE-0002 runs on every check. It verifies the auth service hashes passwords and never returns them in plaintext. GATE-0005 scans payment code for raw card numbers. These run in CI — regressions are caught automatically.

### "Can I add a dependency from orders to analytics?"

```
$ sigil check

GATE-0003: Order Dependency Policy            FAIL
  Order service depends on analytics-service, which is not in the allowed list:
  [catalog-service, cart-service, auth-service, notification-service]
```

GATE-0003 enforces a dependency allowlist. You can still add the dependency — but you have to update the gate first, which means updating the architectural intent, which means someone reviews the *decision*, not just the code.

### "What's the overall health?"

```
$ sigil status

Health: [##################--] 91%
Nodes: 36  |  Edges: 87

$ sigil coverage

Components with spec:    8/9 (89%)
ADRs accepted:           6/7 (86%)

  [+] auth-service: spec, 1 ADR, 1 gate
  [+] catalog-service: spec, 1 ADR, 0 gates
  [~] payment-gateway: spec, 0 ADRs, 1 gate     ← needs an ADR
  [-] admin-dashboard: no spec, 0 ADRs, 0 gates  ← needs everything
```

You see gaps at a glance. The admin dashboard has no spec — someone should write one. The payment gateway has no architectural decision record — was Stripe chosen deliberately or by default?

### The System Map

```
$ sigil map

■ COMP-auth-service
├── ▲ ADR-0002  JWT tokens over sessions  [accepted]
└── ◆ SPEC-0002  JWT Authentication  [accepted]
     └─ ● GATE-0002

■ COMP-catalog-service
├── ▲ ADR-0001  In-memory store  [accepted]
├── ◆ SPEC-0001  Book Catalog API  [accepted]
│    └─ ● GATE-0001
└── ◆ SPEC-0007  Catalog Search Improvements  [proposed]

■ COMP-order-service
├── ▲ ADR-0004  Synchronous checkout orchestration  [accepted]
├── ○ ROLLOUT-0001  Checkout Flow v1 Rollout  [in-progress]
├── ◆ SPEC-0004  Checkout Flow  [accepted]
│    └─ ● GATE-0003
└── ◆ SPEC-0008  Order Status Tracking  [proposed]
```

Every component, its specs, its ADRs, its gates, in one view. Nine services, their relationships, all visible.

---

## The Numbers

|                        | Before        | After           |
|------------------------|---------------|-----------------|
| App code               | 197 lines     | 197 lines       |
| Intent documentation   | 0 files       | 36 files        |
| Answerable questions   | grep + hope   | `sigil why/ask` |
| Enforced constraints   | 0             | 5 gates         |
| Dependency visibility  | implicit      | 87 typed edges  |
| Blast radius analysis  | manual        | `sigil impact`  |
| Coverage tracking      | none          | 91% health      |
| Onboarding time        | read all code | `sigil status`  |

---

## Try It Yourself

```bash
# Clone and explore
git clone https://github.com/fielding/sigil
cd sigil

sigil index --repo examples/demo-app
sigil status --repo examples/demo-app
sigil map --repo examples/demo-app
sigil why services/catalog/routes.py --repo examples/demo-app
sigil impact COMP-order-service --repo examples/demo-app
sigil check --repo examples/demo-app

# Open the interactive viewer
sigil serve --repo examples/demo-app
```

The app code didn't change. What changed is that every question about the system — why, what, who, what-if — now has an answer.

**Humans review intent. Machines enforce constraints. The graph shows the shape of the system.**
