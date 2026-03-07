---
id: ADR-0006
status: accepted
---

# Graph Storage Format

## Context

The intent indexer needs to persist the knowledge graph in a format that the viewer, CI, and search tools can all consume. The graph consists of nodes (components, specs, ADRs, interfaces, gates) and typed edges (belongs_to, decided_by, depends_on, etc.).

?? We considered a database but decided it was overkill for a repo-local tool.

## Decision

Use a single JSON file (`.intent/index/graph.json`) as the canonical graph artifact. Structure:

```json
{
  "version": "1.0",
  "generated_at": "ISO-8601 timestamp",
  "nodes": [
    {
      "id": "SPEC-0001",
      "type": "spec",
      "title": "Intent-First Review System",
      "path": "intent/intent-system/specs/SPEC-0001-intent-first-review-system.md",
      "body_summary": "First 500 chars of markdown body...",
      "frontmatter": { "id": "SPEC-0001", "status": "accepted" }
    }
  ],
  "edges": [
    {
      "type": "belongs_to",
      "src": "SPEC-0001",
      "dst": "COMP-intent-system",
      "confidence": 1.0,
      "evidence": ["Links block"]
    }
  ]
}
```

Key design choices:

1. **body_summary** (max 500 chars) -- enables content search and preview without loading source files
2. **frontmatter** object -- enables the viewer to show status badges and the coverage engine to score document maturity
3. **confidence + evidence** on edges -- not all edges are explicit; some are inferred from paths or wikilinks
4. **Flat arrays** -- no nesting, easy to parse in any language

A secondary `search.json` with lightweight node records is also generated for autocomplete use cases.

## Alternatives

1. **SQLite** -- full query power, but adds a binary dependency and doesn't diff well in git. Rejected.
2. **Multiple JSON files** (one per node) -- avoids large single files, but complicates viewer loading. Rejected.
3. **YAML graph** -- more readable, but slower to parse and D3 expects JSON anyway. Rejected.

## Consequences

- Single file load in the viewer (one fetch for the entire graph)
- Git-friendly: graph.json can be diffed and tracked
- Regenerated on every `sigil index` -- not a source of truth, just a cache
- Will need pagination or streaming if graphs exceed ~10,000 nodes

!! If graph.json ever becomes a bottleneck, consider splitting into chunks or adding lazy loading.

>> See [[SPEC-0004]] for the CLI commands that produce this file.

## Links

- For: [[SPEC-0004]]
- Belongs to: [[COMP-intent-system]]
