---
id: SPEC-0004
status: accepted
---

# Sigil CLI

## Intent

Provide a single command-line tool that manages the full lifecycle of intent documents: scaffolding, indexing, linting, searching, and diffing. The CLI is the kernel that everything else builds on.

!! If the CLI is slow or unreliable, nothing else works. Keep it fast and dependency-light.

## Context

Engineers already live in their terminal. A CLI that fits into existing workflows (git hooks, CI, editor tasks) has zero adoption friction. We chose Python because it's universal and the YAML/markdown parsing ecosystem is mature.

>> See [[ADR-0002]] for the repo schema that the CLI operates on.

## Goals

- **index** -- build the knowledge graph from repo contents into `.intent/index/graph.json`
- **lint** -- validate intent documents (front matter, required sections, dangling refs)
- **new** -- scaffold new specs/ADRs from templates with auto-incrementing IDs
- **diff** -- compute structural graph changes between two git commits
- **fmt** -- normalize front matter and ensure Links sections exist
- **bootstrap** -- scan a repo for manifest files and create component stubs
- **init** -- zero-to-working setup: scaffold dirs, bootstrap, index, open viewer
- **ask** -- local keyword search across the intent corpus

## Non-goals

- GUI or TUI interface (use the viewer for that)
- Package manager distribution yet (run from source for now)
- LLM-powered features in the core CLI (keep it offline-first)

## Design

### Single-file architecture

Everything lives in `tools/intent/sigil.py`. No package structure, no setup.py. One file, one entry point.

?? Will this scale past 2000 lines? Probably fine for now. Split when it hurts.

### Graph model

- **Node**: id, type, title, path, body_summary
- **Edge**: type, src, dst, confidence, evidence
- **Graph**: dict of nodes + list of edges

Nodes are discovered from four directory scanners (components, interfaces, intent docs, gates). Edges come from three sources: typed Links blocks, path-inferred belongs_to, and wikilink-derived relates_to.

### Output artifacts

- `graph.json` -- full graph with frontmatter enrichment
- `search.json` -- lightweight index for autocomplete/search

## Links

- Belongs to: [[COMP-intent-system]]
- Depends on: [[ADR-0002]]
- Decided by: [[ADR-0004]]

## Acceptance Criteria

- [x] All 7 commands work: index, lint, new, diff, fmt, bootstrap, init
- [x] 45+ tests passing
- [x] graph.json includes body_summary and frontmatter fields
- [x] Zero external dependencies beyond PyYAML
- [x] Runs on Python 3.11+
- [ ] `ask` command with local keyword search
