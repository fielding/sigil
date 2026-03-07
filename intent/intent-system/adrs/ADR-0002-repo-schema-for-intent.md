---
id: ADR-0002
status: accepted
---

# Repo Schema for Intent

## Context

Intent artifacts need a home. They could live in a database, a wiki, or the repo itself. We need a convention that is portable, versionable, and doesn't require a running service.

## Decision

Store all intent artifacts in the git repo using a structured directory layout:

- `/components/` — component registry (YAML)
- `/intent/<component>/specs/` — spec documents (Markdown + front matter)
- `/intent/<component>/adrs/` — decision records
- `/interfaces/` — contract definitions (OpenAPI, protobuf, JSON Schema)
- `/gates/` — constraint definitions (YAML)
- `/.intent/` — tooling config and generated index

Front matter provides machine-readable metadata (id, status). Markdown body provides human-readable content. `[[ID]]` wikilinks create typed relationships.

## Alternatives

1. **External database** — queryable but not versionable, not portable
2. **Wiki (Notion, Confluence)** — easy to write but disconnected from code, no enforcement
3. **Inline code annotations** — close to code but hard to get a system view

## Consequences

- Repo is the source of truth; no external dependency
- Git history tracks intent evolution
- Tooling (CLI, editor, CI) reads directly from the filesystem
- Requires discipline: teams must follow conventions

## Links

- For: [[SPEC-0001]]
