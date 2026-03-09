# Shelf — A Sigil Demo Bookstore

Shelf is a small bookstore web application built to demonstrate what **intent-first engineering** looks like in practice using [Sigil](../../README.md).

The app itself is intentionally simple (~150 lines of Python). The interesting part is the intent layer — the specs, ADRs, interfaces, gates, and component graph that describe *what* the system does, *why* it was built this way, and *what constraints* protect it.

## Architecture

```
+-------------+     +------------------+     +---------------+
|   web-app   |---->| catalog-service  |     | notification  |
|  (Next.js)  |---->|   (books API)    |     |   service     |
+-------------+     +------------------+     +---------------+
      |                                             ^
      v                                             |
+-------------+     +------------------+            |
| auth-service|     |  order-service   |------------+
|  (JWT auth) |     | (checkout flow)  |
+-------------+     +------------------+
      ^                    ^
      |                    |
+-------------+            |
| cart-service |----------+
| (session cart)|
+-------------+
```

```
+------------------+     +------------------+
| payment-gateway  |     |  search-service  |
| (Stripe stub)    |     |  (search index)  |
+------------------+     +------------------+
         |                        |
         v                        v
+------------------+     +------------------+
|  order-service   |     | catalog-service  |
+------------------+     +------------------+

+------------------+
| admin-dashboard  |----> catalog, orders, auth
+------------------+
```

**36 nodes, 96 edges** — 9 components, 5 API interfaces, 9 specs, 7 ADRs, 5 gates, 1 rollout plan.

## Quick Start

From the sigil repo root (install sigil first: `pip install sigil-cli`):

```bash
# Index the intent graph
sigil index --repo examples/demo-app

# See the system at a glance
sigil status --repo examples/demo-app

# Print the component map
sigil map --repo examples/demo-app

# Open the interactive viewer in your browser
sigil serve --repo examples/demo-app
```

## What You Can Do

### Trace intent for any file

Ask "why does this file exist?" and get the full chain: component, specs, ADRs, gates.

```bash
sigil why services/catalog/routes.py --repo examples/demo-app
```

### Enforce constraints with gates

Five gates enforce real rules — API compatibility, security, dependency policy, spec quality, PCI compliance:

```bash
sigil --repo examples/demo-app check
```

### Detect drift

Find files that aren't mapped to any component:

```bash
sigil --repo examples/demo-app drift
```

### Review changes

See how code changes relate to intent — which specs govern them, which gates apply:

```bash
sigil --repo examples/demo-app review
```

### Search the intent graph

Ask questions in natural language:

```bash
sigil --repo examples/demo-app ask "how does authentication work"
sigil --repo examples/demo-app ask "checkout flow"
```

### Check intent coverage

See which components are well-documented and which need attention. The dashboard shows green/yellow/red health per component:

```bash
sigil --repo examples/demo-app coverage
```

This project intentionally has mixed coverage — some components are fully documented, others have gaps — to show what the Coverage Dashboard looks like on a real codebase.

### Visualize blast radius

See what's affected when a component changes. The Impact Radar shows concentric rings of dependencies:

```bash
sigil --repo examples/demo-app impact COMP-order-service
sigil --repo examples/demo-app impact COMP-payment-gateway
```

### Lint intent docs

Verify all specs, ADRs, and components follow conventions:

```bash
sigil --repo examples/demo-app lint
```

### Export a standalone viewer

Generate a self-contained HTML file with the interactive graph:

```bash
sigil --repo examples/demo-app export
```

## CI/CD Integration

Sigil fits into your existing CI pipeline. The included workflow (`.github/workflows/sigil.yml`) runs on every pull request and:

1. **Validates** — `sigil ci` indexes the graph, lints docs, checks gates, and reports coverage
2. **Enforces gates** — `sigil check` fails the build if any blocking gate is violated
3. **Detects drift** — `sigil drift` warns about source files not mapped to any component
4. **Diffs the graph** — `sigil diff` shows which intent nodes changed in the PR
5. **Posts a PR comment** — `sigil pr` summarizes coverage, gates, and drift on the pull request

To adopt this in your own repo, copy `.github/workflows/sigil.yml` and adjust the install step:

```yaml
# From PyPI
- run: pip install sigil-cli

# Or from source
- run: pip install git+https://github.com/fielding/sigil.git
```

The workflow uploads graph snapshots and the standalone viewer as build artifacts, so reviewers can explore the intent graph directly from CI.

## What This Demonstrates

This demo answers: **"What does intent-first engineering look like in practice?"**

| Layer | What it does | Example |
|-------|-------------|---------|
| **Components** | Register services with ownership, dependencies, data classification | `components/order-service.yaml` |
| **Specs** | Describe features — intent, goals, non-goals, acceptance criteria | `intent/catalog-service/specs/SPEC-0001-book-catalog-api.md` |
| **ADRs** | Document architectural decisions with context and alternatives | `intent/auth-service/adrs/ADR-0002-jwt-over-sessions.md` |
| **Interfaces** | Define API contracts with provider/consumer relationships | `interfaces/API-CATALOG-V1/README.md` |
| **Gates** | Enforce constraints tied to intent nodes | `gates/GATE-0001-catalog-api-compat.yaml` |
| **Rollouts** | Track feature rollout phases with prerequisites and rollback | `intent/order-service/rollouts/ROLLOUT-0001-checkout-v1.md` |

The app code is ~150 lines of Python stubs. The intent layer is ~40 files that tell you everything about what the system does, why, and what protects it.

**Humans review intent. Machines enforce constraints. The graph shows the shape of the system.**

See [DEMO.md](DEMO.md) for a guided walkthrough with expected output.
