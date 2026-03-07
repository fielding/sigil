---
id: API-INTENT-CLI-V1
status: active
---

# Intent CLI Interface v1

The Sigil CLI exposes 15 commands that operate on the intent graph. This interface is consumed by the viewer (via `sigil serve` HTTP API) and CI (via direct CLI invocation).

## Commands

| Command | Input | Output | Used by |
|---------|-------|--------|---------|
| `index` | repo root | graph.json, search.json | viewer, CI |
| `status` | repo root | terminal health report | developer |
| `diff` | base SHA, head SHA | diff.json, diff.md | CI |
| `new` | type, component, title | new intent doc | viewer (via API), developer |
| `lint` | repo root | lint results | CI |
| `check` | repo root | gate results | CI |
| `drift` | repo root | drift.json | viewer, CI |
| `timeline` | repo root | timeline.json | viewer, CI |
| `export` | repo root | self-contained HTML | CI, developer |
| `badge` | repo root | badge.svg | CI |
| `serve` | port | HTTP server + file watcher | viewer |
| `ask` | query | search results | developer |
| `init` | repo root | scaffolded repo + running server | developer |
| `fmt` | repo root | normalized docs | developer |
| `bootstrap` | repo root | component stubs | developer |

## HTTP API (via `sigil serve`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/new` | POST | Create a new intent document |
| `/**` | GET | Static file serving for viewer |

## Links

- Provided by: [[COMP-intent-system]]
- Consumed by: [[COMP-sigil-viewer]], [[COMP-sigil-ci]]
