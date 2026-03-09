# Adopting Sigil in an Existing Project

A step-by-step guide to adding intent-first engineering to a codebase you already have.

---

## Prerequisites

- Python 3.9+
- A git repository with at least one service or module
- ~15 minutes

## Step 1: Install Sigil

Clone the Sigil repository and add the CLI to your path:

```bash
git clone https://github.com/fielding/sigil.git ~/sigil
alias sigil="python3 ~/sigil/tools/intent/sigil.py"
```

Verify it works:

```bash
sigil --version
```

## Step 2: Initialize your repo

Navigate to your project root and run:

```bash
cd ~/my-project
sigil init
```

This does six things automatically:

1. Creates the directory structure (`components/`, `intent/`, `interfaces/`, `gates/`)
2. Copies starter templates into `templates/`
3. Scans for language manifests (`package.json`, `pyproject.toml`, `go.mod`, etc.) and creates component stubs
4. Adds `.intent/index/` to `.gitignore`
5. Builds the initial graph index
6. Opens the interactive viewer in your browser

After running, your repo will have new files:

```
my-project/
├── components/
│   ├── api.yaml            # auto-detected from api/package.json
│   └── worker.yaml         # auto-detected from worker/pyproject.toml
├── intent/
│   ├── api/
│   │   └── specs/
│   │       └── SPEC-0001-api-overview.md
│   └── worker/
│       └── specs/
│           └── SPEC-0002-worker-overview.md
├── gates/
├── interfaces/
├── templates/
│   ├── SPEC.md
│   ├── ADR.md
│   ├── COMPONENT.yaml
│   ├── GATE.yaml
│   └── INTERFACE.md
└── .intent/
    ├── config.yaml
    └── index/              # gitignore'd — generated artifacts
```

> **Tip:** If you want to preview what `init` would detect without creating files, run `sigil bootstrap --dry-run` first.

## Step 3: Check your health score

```bash
sigil status
```

You'll see something like:

```
╭─ my-project ─────────────────────────────────╮
│  Health  42%  ██████░░░░░░░░                  │
│  Nodes   4   (2 components, 2 specs)          │
│  Edges   2   (2 belongs_to)                   │
╰───────────────────────────────────────────────╯
```

42% is normal for a fresh init — you haven't written real specs or ADRs yet. The score is calculated from four weighted metrics:

| Metric                    | Weight | What it measures                              |
|---------------------------|--------|-----------------------------------------------|
| Components with specs     | 40%    | Every component has at least one spec          |
| ADRs accepted             | 30%    | Architectural decisions are documented          |
| Specs with acceptance     | 20%    | Specs include testable acceptance criteria      |
| No dangling references    | 10%    | All `[[wikilinks]]` resolve to real nodes       |

Run `sigil coverage` for the full breakdown, including per-component red/yellow/green status.

## Step 4: Edit your first spec

Open one of the auto-generated specs and make it real. Sigil created a skeleton — now fill it in:

```bash
$EDITOR intent/api/specs/SPEC-0001-api-overview.md
```

Write it like you'd explain the service to a new teammate:

```markdown
---
id: SPEC-0001
status: accepted
---

# API Service

## Intent

The API service is the public HTTP gateway for our application.
It handles authentication, request validation, and routes to
internal services.

## Context

We started with a monolith. The API layer was extracted in Q3 2024
to allow the worker and API to scale independently.

## Goals

- Serve all public HTTP traffic behind a single domain
- Validate and authenticate every request before forwarding
- Rate-limit by API key

## Non-goals

- Business logic — that lives in the worker
- Direct database access

## Design

Express.js app behind nginx. Routes are versioned (`/v1/`, `/v2/`).
Auth uses JWT with refresh tokens (see ADR-0001).

## Links

- Belongs to: [[COMP-api]]
- Provides: [[API-PUBLIC-V1]]
- Consumes: [[API-WORKER-INTERNAL-V1]]
- Decided by: [[ADR-0001]]

## Acceptance Criteria

- [ ] All endpoints return structured errors with status codes
- [ ] Auth middleware rejects expired tokens with 401
- [ ] Rate limiter returns 429 with Retry-After header
```

After saving, re-index to pick up your changes:

```bash
sigil index
sigil status
```

Your health score will jump — you now have a real spec with acceptance criteria.

## Step 5: Document a decision

Every project has decisions worth capturing. Create an ADR:

```bash
sigil new adr api "JWT over session cookies"
```

This creates `intent/api/adrs/ADR-0001-jwt-over-session-cookies.md`. Edit it:

```markdown
---
id: ADR-0001
status: accepted
---

# JWT over session cookies

## Context

We need stateless auth for horizontal scaling. Session cookies
require a shared session store (Redis), which adds operational
complexity we don't need yet.

## Decision

Use short-lived JWTs (15 min) with long-lived refresh tokens
(30 days) stored in httpOnly cookies.

## Alternatives

- **Session cookies + Redis:** More familiar, but adds infrastructure.
- **OAuth2 with external IdP:** Overkill for our current user base.

## Consequences

- Token revocation requires a deny-list or short TTLs.
- Refresh token rotation must be implemented to prevent replay.
- Client code must handle 401 → refresh → retry flow.

## Links

- For: [[SPEC-0001]]
```

## Step 6: Define an interface

If your service exposes an API, document the contract:

```bash
sigil new interface API-PUBLIC-V1 "Public REST API"
```

Edit `interfaces/API-PUBLIC-V1/README.md`:

```markdown
---
id: API-PUBLIC-V1
type: api
status: active
---

# Public REST API

## Description

Versioned REST API serving all client applications. Currently at v1.

## Contract

OpenAPI spec at `api/openapi.yaml`.

## Links

- Provided by: [[COMP-api]]
- Consumed by: [[COMP-web-frontend]]
```

## Step 7: Add a gate

Gates enforce constraints automatically. Create one:

```bash
sigil new gate "API schema validation" --applies-to COMP-api
```

Edit the generated gate file in `gates/`:

```yaml
id: GATE-0001
type: command
status: active

applies_to:
  - node: COMP-api
  - node: API-PUBLIC-V1

enforced_by:
  kind: command
  workdir: api/
  command: ["npx", "swagger-cli", "validate", "openapi.yaml"]

policy:
  mode: "enforce"
  on_fail: "block"

docs:
  summary: "OpenAPI spec must be valid"
  owner: "platform-team"
```

Run your gates:

```bash
sigil check
```

```
Gates
  ✓ GATE-0001  API schema validation       PASS

1 passed, 0 failed
```

Gates can also be pattern-based (check that files match or don't match a regex) or threshold-based (require a minimum coverage score). See `templates/GATE.yaml` for all options.

## Step 8: See what's drifting

Sigil can detect source files that aren't mapped to any component:

```bash
sigil drift
```

```
Unmapped paths (not covered by any component):
  scripts/deploy.sh
  migrations/
  docker-compose.yaml

3 files not mapped to any component
```

Fix this by updating the `paths` field in your component YAML files, or by creating a new component for shared infrastructure:

```bash
sigil new component infra "Infrastructure & Deploy"
```

Then add `paths: ["scripts/**", "migrations/**", "docker-compose.yaml"]` to `components/infra.yaml`.

## Step 9: Explore your intent graph

Start the live viewer:

```bash
sigil serve
```

This opens an interactive D3 visualization at `http://localhost:8787` with 8 views:

| Key | View           | Shows                                      |
|-----|----------------|--------------------------------------------|
| `g` | **Graph**      | Force-directed knowledge graph              |
| `r` | **Radar**      | Blast radius from any node                  |
| `h` | **Hierarchy**  | Layered: Components → Specs → ADRs          |
| `c` | **Coverage**   | Health score with per-component cards        |
| `d` | **Drift**      | Files not mapped to components               |
| `t` | **Timeline**   | Git-backed evolution history                 |
| `m` | **Matrix**     | Dependency heatmap                           |
| `w` | **Review**     | Governance snapshot                          |

Use `Cmd+K` to open the command palette, `/` to search, and click any node for details.

## Step 10: Integrate with CI

Create `.github/workflows/sigil.yaml`:

```yaml
name: Sigil Intent Check

on:
  pull_request:
    branches: [main]

jobs:
  intent-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # needed for timeline and diff

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Sigil
        run: |
          git clone https://github.com/fielding/sigil.git /tmp/sigil
          echo "alias sigil='python3 /tmp/sigil/tools/intent/sigil.py'" >> ~/.bashrc

      - name: Run Sigil CI pipeline
        run: |
          python3 /tmp/sigil/tools/intent/sigil.py ci \
            --repo . \
            --base ${{ github.event.pull_request.base.sha }} \
            --head ${{ github.sha }}

      - name: Upload coverage badge
        uses: actions/upload-artifact@v4
        with:
          name: sigil-badge
          path: .intent/badge.svg
```

The `sigil ci` command runs the full pipeline in one shot:

1. **Index** — Rebuild the graph
2. **Lint** — Check for structural issues
3. **Check** — Run all gates
4. **Badge** — Generate coverage badge
5. **Review** — Analyze changed files for intent coverage

Add `--strict` to fail the build on warnings (not just errors).

### PR comments

For automatic PR comments showing intent coverage of changed files:

```yaml
      - name: Post intent review
        if: github.event_name == 'pull_request'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python3 /tmp/sigil/tools/intent/sigil.py pr \
            --repo . \
            --base ${{ github.event.pull_request.base.sha }} \
            --head ${{ github.sha }}
```

This posts a comment on the PR showing which changed files are covered by specs and which are drifting.

### Pre-commit hook

For local enforcement, install the git hook:

```bash
sigil hook install
```

This runs `sigil lint` before every commit and blocks if there are errors.

## Step 11: Configure rules

Edit `.intent/config.yaml` to customize behavior:

```yaml
version: "1.0"
project: my-project

paths:
  components: components/
  intent: intent/
  interfaces: interfaces/
  gates: gates/
  index: .intent/index/

id_counters:
  SPEC: 3
  ADR: 2
  GATE: 2
  RISK: 1
  ROLLOUT: 1
```

The `id_counters` auto-increment when you use `sigil new`. The `paths` section lets you relocate directories if your repo has a non-standard layout.

## Everyday commands

Once set up, these are the commands you'll use most:

```bash
# What's the health of my project?
sigil status

# Search intent docs
sigil ask "how does auth work"

# Why does this file exist?
sigil why src/api/middleware/auth.ts

# What breaks if I change this component?
sigil impact COMP-api

# Validate everything
sigil check

# Visualize
sigil serve
```

## What to commit

Commit everything except `.intent/index/`:

```
✓ components/*.yaml        — component registry
✓ intent/**/*.md           — specs and ADRs
✓ interfaces/**/README.md  — API contracts
✓ gates/*.yaml             — gate definitions
✓ templates/*              — document templates
✓ .intent/config.yaml      — project config

✗ .intent/index/           — generated (gitignore'd)
```

## Next steps

- Add specs for your remaining components (`sigil coverage` shows gaps)
- Write ADRs for past decisions that new hires always ask about
- Set up gates for your most important invariants
- Run `sigil export` to share a snapshot with stakeholders
- Check the [demo app](../examples/demo-app/) for a fully instrumented example

---

*Built with [Sigil](https://github.com/fielding/sigil) — intent-first engineering for teams that want to know why.*
