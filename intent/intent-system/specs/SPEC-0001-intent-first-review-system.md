---
id: SPEC-0001
status: accepted
---

# Intent-First Review System

## Intent

Replace diff-centric code review with intent-centric review. Humans review what and why; machines verify that code conforms to stated intent.

## Context

Code review today is broken at scale. Reviewers scroll through thousands of lines of diffs without understanding the purpose, constraints, or risks of a change. This leads to rubber-stamping, slow cycles, and missed architectural issues.

## Goals

- Intent documents (specs, ADRs, interfaces, gates) become the primary review surface
- A dependency graph connects components, interfaces, specs, and constraints
- CI enforces conformance via gates tied to intent nodes
- Adoption is low-friction: CLI-first, editor-integrated, repo-portable

## Non-goals

- Replacing version control (git remains the storage layer)
- Eliminating all human review (humans still review intent; machines review implementation)
- Building a full project management tool

## Design

The system has four layers:

1. **Repo conventions** — structured directories for components, intent docs, interfaces, and gates
2. **CLI/indexer** — parses repo into a graph, produces diffs, runs lints
3. **Editor plugin** — autocomplete for `[[ID]]` references, quick-fixes, inline lint
4. **Platform UI** — graph explorer, intent review view, impact analysis, drift dashboard

### Core node types

- Component (COMP-*): a service, package, or module
- Spec (SPEC-*): an intent plan describing what and why
- Decision (ADR-*): architectural decision records
- Interface (API-*, EVT-*, SCHEMA-*, PROTO-*): contract definitions
- Gate (GATE-*): enforceable constraints tied to nodes

### Edge vocabulary

- belongs_to, decided_by, provides, consumes, depends_on, gated_by, supersedes, relates_to

## Links

- Belongs to: [[COMP-intent-system]]

## Acceptance Criteria

- [ ] Repo schema supports all core node types
- [ ] CLI can index repo into graph.json
- [ ] CLI can compute graph diff between two commits
- [ ] Templates exist for all core node types
- [ ] CI can post intent diff as PR comment
- [ ] Editor plugin provides autocomplete for [[ID]] references
