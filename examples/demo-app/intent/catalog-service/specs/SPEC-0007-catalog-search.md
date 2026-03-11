---
id: SPEC-0007
status: proposed
---

# Catalog Search Improvements

## Intent

Upgrade the catalog search from basic substring matching to something that handles typos, partial words, and relevance ranking. This makes the storefront usable for real browsing, not just exact-match lookups.

## Context

The current search (SPEC-0001) does case-insensitive substring matching on title and author. That's fine for 3 books, but falls apart with a real catalog. Users expect search to be forgiving — "pragmatc progrmmr" should still find the right book.

This spec supersedes the search portion of [[SPEC-0001]] without changing the catalog listing or lookup endpoints.

## Goals

- Fuzzy matching that tolerates typos (edit distance <= 2)
- Results ranked by relevance (exact match > prefix > fuzzy)
- Still fast enough for typeahead (sub-50ms for catalogs under 10k books)

## Non-goals

- Elasticsearch or external search infrastructure
- Faceted search / filters
- Search analytics or query logging

## Design

Replace the substring filter with a scoring function:
1. Exact substring match: score 1.0
2. Prefix match: score 0.8
3. Levenshtein distance <= 2: score 0.5
4. No match: excluded

Results sorted by score descending. The endpoint signature doesn't change — same `GET /api/catalog/search?q=` contract.

## Links

- Belongs to: [[COMP-catalog-service]]
- Provides: [[API-CATALOG-V1]]
- Supersedes: [[SPEC-0001]]
- Gates: [[GATE-0001]]

## Acceptance Criteria

- [ ] "pragmatc" returns "The Pragmatic Programmer"
- [ ] Exact matches rank higher than fuzzy matches
- [ ] Performance stays under 50ms for 10k books
- [ ] API contract (request/response shape) is unchanged
