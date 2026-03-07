---
id: ADR-0004
status: accepted
---

# IDs and Wikilinks

## Context

Nodes in the intent graph need stable, human-readable identifiers. Relationships between nodes need a lightweight syntax that works in plain Markdown.

## Decision

- Every node gets a prefixed ID: `SPEC-0042`, `ADR-0001`, `COMP-user-service`, `API-USER-V1`, `GATE-0021`
- IDs are declared in YAML front matter (`id: SPEC-0042`)
- References use `[[ID]]` wikilink syntax: `[[COMP-user-service]]`, `[[API-USER-V1]]`
- Typed relationships use a `## Links` section with labeled entries:
  ```
  - Belongs to: [[COMP-user-service]]
  - Provides: [[API-USER-V1]]
  ```
- The CLI resolves wikilinks to file paths via the generated index

## Alternatives

1. **UUIDs** — stable but unreadable
2. **File paths as IDs** — fragile across renames
3. **Custom DSL** — higher learning curve than Markdown conventions

## Consequences

- IDs are grep-friendly and human-readable
- Wikilinks are familiar (Obsidian, Notion, wiki conventions)
- Renaming requires updating references (mitigated by `intent fmt`)
- Tooling must maintain an ID-to-path mapping

## Links

- For: [[SPEC-0001]]
