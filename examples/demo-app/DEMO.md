# Shelf Demo Walkthrough

This guide walks through the Sigil intent layer on the Shelf bookstore app. Each section shows a different capability — from system maps to gate enforcement to natural language search.

All commands assume you're in the sigil repo root.

---

## 1. Index the graph

Before anything else, build the intent graph:

```bash
sigil --repo examples/demo-app index
```

```
Indexed 36 nodes, 87 edges
Wrote .intent/index/graph.json and search.json
```

---

## 2. See the system map

```bash
sigil --repo examples/demo-app map
```

This prints the full component graph: 9 components, their specs, ADRs, gates, and relationships. You can see at a glance that the order service is the most connected component (it depends on 5 others) and that the catalog API is the most consumed interface.

---

## 3. Check system health

```bash
sigil --repo examples/demo-app status
```

```
Sigil Intent Status
====================
Health: [##################--] 91%

Nodes: 36
  component: 9
  spec: 9
  adr: 7
  gate: 5
  interface: 5
Edges: 87
```

36 nodes across 6 types, 87 typed edges (belongs_to, provides, consumes, depends_on, decided_by, gated_by, supersedes, relates_to). Health is 91% — some components still need specs or have proposed ADRs.

---

## 3b. Check intent coverage

```bash
sigil --repo examples/demo-app coverage
```

```
Intent Coverage: 91% (excellent)

Components with spec:    8/9 (89%)
ADRs accepted:           6/7 (86%)

Components:
  [+] COMP-auth-service: spec, 1 ADR(s), 1 gate(s)
  [+] COMP-catalog-service: spec, 1 ADR(s), 0 gate(s)
  [~] COMP-payment-gateway: spec, 0 ADR(s), 1 gate(s)
  [~] COMP-search-service: spec, 0 ADR(s), 0 gate(s)
  [-] COMP-admin-dashboard: no spec, 0 ADR(s), 0 gate(s)
```

Coverage shows green `[+]` for components with both spec and ADR, yellow `[~]` for partial, and red `[-]` for missing. This is intentional — real projects always have gaps. The Coverage Dashboard in the viewer (`c` key) renders this as visual cards.

---

## 3c. Visualize blast radius

```bash
sigil --repo examples/demo-app impact COMP-order-service
```

Shows concentric rings of impact when the order service changes — direct dependencies (specs, gates), secondary (the services it calls), and tertiary (their ADRs and specs). The order service has a blast radius of 32 nodes.

```bash
sigil --repo examples/demo-app impact COMP-payment-gateway
```

The payment gateway reaches 21 nodes through its connection to the order service. In the viewer (`r` key), this renders as an interactive radar visualization.

---

## 4. Understand why a file exists

Pick any source file and ask Sigil to trace its intent chain:

```bash
sigil --repo examples/demo-app why services/catalog/routes.py
```

Output shows:
- **Who owns it**: Catalog Service (COMP-catalog-service)
- **What is being built**: SPEC-0001 (Book Catalog API), SPEC-0007 (Search Improvements)
- **Why it was built this way**: ADR-0001 (in-memory store chosen over Postgres/SQLite)
- **What enforces it**: GATE-0001 (API compatibility check)

Try it on other files:
```bash
sigil --repo examples/demo-app why services/auth/auth.py
sigil --repo examples/demo-app why services/orders/orders.py
```

---

## 5. Enforce gates

Gates are constraints tied to intent nodes. Run them all:

```bash
sigil --repo examples/demo-app check
```

```
GATE-0001: Catalog API Compatibility    PASS
GATE-0002: Auth Security                PASS
GATE-0003: Order Dependency Policy      PASS
GATE-0004: Spec Quality                 PASS
GATE-0005: Payment PCI Compliance       PASS

Gates: 5 passed, 0 failed, 0 warning(s)
```

Five gates enforce real rules:
- **GATE-0001** (command): Verifies catalog API endpoints exist and prices use integer cents
- **GATE-0002** (command): Verifies auth service hashes passwords and never returns plaintext
- **GATE-0003** (builtin): Verifies order service only depends on allowed components
- **GATE-0004** (builtin): Verifies all specs have required sections
- **GATE-0005** (pattern): Verifies payment code never references raw card numbers

**Try breaking a gate** — edit `services/catalog/routes.py` and rename `list_books` to something else, then re-run `check`. GATE-0001 will fail with a clear error explaining what broke and why.

---

## 6. Detect drift

Find files that aren't mapped to any component:

```bash
sigil --repo examples/demo-app drift
```

```
Files scanned: 56
Files mapped to components: 6
Unowned files: 2

DRIFT: 2 file(s) not mapped to any component
  - DEMO.md
  - README.md
```

Drift detection surfaces files that exist outside the intent graph — code that nobody owns, docs that aren't governed. In this demo, only the top-level docs are unowned (intentionally).

---

## 7. Review changes

See how code changes relate to intent:

```bash
sigil --repo examples/demo-app review
```

This shows:
- **Intent coverage**: What percentage of changed files are governed by components
- **Governed changes**: Code files mapped to components, with their specs, ADRs, and gates
- **Ungoverned changes**: Files not mapped to any component
- **Suggestions**: Run `sigil suggest <path>` for governance recommendations

In a real PR workflow, `sigil review` answers: "Does this change have intent backing it?"

---

## 8. Search the intent graph

Ask questions in natural language and get ranked results with context snippets:

```bash
sigil --repo examples/demo-app ask "how does authentication work"
```

```
Query: how does authentication work
1 result(s)

[ADR] ADR-0002  Use JWT tokens instead of server-side sessions
  | We need authentication across multiple services...
```

More queries to try:
```bash
sigil --repo examples/demo-app ask "checkout"
sigil --repo examples/demo-app ask "why in-memory"
sigil --repo examples/demo-app ask "notification"
```

Search uses fuzzy matching with section-aware ranking — IDs and titles score higher than body text.

---

## 9. Lint the intent docs

```bash
sigil --repo examples/demo-app lint
```

```
Lint: 0 warning(s), 0 error(s)
```

Zero warnings. Every spec has acceptance criteria, every ADR has a Links section, every component has an owner. (Coverage gaps like missing specs don't produce lint warnings — they surface in `sigil coverage` instead.)

---

## 10. Open the interactive viewer

```bash
sigil --repo examples/demo-app serve
```

Opens a browser with an interactive force-directed graph. Eight views are available:

| Key | View | What it shows |
|-----|------|--------------|
| `g` | Graph | Force-directed node graph with typed edges |
| `r` | Impact Radar | Concentric rings showing blast radius |
| `h` | Hierarchy | Tree layout of component ownership |
| `c` | Coverage | Spec and gate coverage per component |
| `d` | Drift | Files not mapped to components |
| `t` | Timeline | Intent changes over time (requires git history) |
| `m` | Matrix | Component dependency matrix |
| `w` | Review | Governance review dashboard |

Click any node to see its details, edges, and connections.

---

## 11. Export a standalone viewer

```bash
sigil --repo examples/demo-app export
```

Generates a self-contained HTML file with all graph data embedded. Share it, host it on GitHub Pages, or open it offline — no server needed.

---

## What this demonstrates

This demo answers: **"What does intent-first engineering look like in practice?"**

- Every service has a component registration declaring ownership and dependencies
- Every feature has a spec describing what, why, goals, non-goals, and acceptance criteria
- Every architectural choice has an ADR explaining the decision and alternatives considered
- API contracts are defined as interfaces with clear provider/consumer relationships
- Gates enforce real constraints (API compatibility, security, dependency policy, spec quality, PCI compliance)
- Coverage dashboard shows realistic mixed health — green, yellow, and red components
- Impact radar visualizes blast radius for any node in the graph
- A rollout plan tracks the checkout feature from development through production
- The intent graph connects everything with typed edges

The app code is ~150 lines of Python stubs. The intent layer is ~40 files that tell you everything about what the system does, why, and what protects it.

**Humans review intent. Machines enforce constraints. The graph shows the shape of the system.**
