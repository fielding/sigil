---
id: ADR-0007
status: proposed
---

# Dedicated search service instead of in-catalog search

## Context

Search is currently handled inside the catalog service (see [[SPEC-0007]]). As the catalog grows, search needs its own index, ranking logic, and potentially a different data store (e.g., Elasticsearch). Running search queries against the primary catalog store creates contention.

The question is whether to extract search into its own service now or keep it coupled to the catalog.

## Decision

Extract search into a dedicated service that maintains its own index built from catalog data. The search service consumes the Catalog API to build and refresh its index, but serves queries independently.

This decision is still **proposed** — we haven't committed to the migration yet. SPEC-0007 covers the immediate fuzzy search improvements inside the catalog service. This ADR captures the longer-term direction.

## Alternatives

- **Keep search in catalog**: Simpler, fewer moving parts. But search and catalog have different scaling characteristics — search is read-heavy with complex ranking, catalog is CRUD with consistency requirements.
- **Use a managed search service (Algolia, Typesense)**: Offloads the problem entirely. But adds an external dependency and costs money for what's currently a simple feature.
- **Client-side search**: Ship the catalog to the browser and search there. Works for small catalogs but doesn't scale.

## Consequences

- Search service needs its own data refresh mechanism (poll or event-driven)
- Catalog service gets simpler — just CRUD, no search logic
- Two services to deploy and monitor instead of one
- Search can scale independently (more replicas, different instance type)
- Index staleness becomes a concern — search results may lag behind catalog updates

## Links

- For: [[COMP-search-service]]
- Relates to: [[SPEC-0007]]
- Relates to: [[COMP-catalog-service]]
