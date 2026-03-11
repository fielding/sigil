---
id: SPEC-0001
status: accepted
---

# Book Catalog API

## Intent

Provide a read-only API for browsing and searching the book inventory. This is the foundational data service — everything else (cart, orders, search) depends on being able to look up books by ID and list what's available.

## Context

We need a single source of truth for book data. The web app needs it for product pages, the cart service needs it to validate items, and the order service needs it to lock in prices at checkout time. Without a clean catalog API, every service would either duplicate book data or reach directly into the database.

## Goals

- Expose book listing, lookup by ID, and text search
- Keep it read-only (writes go through a separate admin flow, out of scope)
- Sub-100ms response times for all endpoints
- Return enough data for the frontend to render product cards without extra calls

## Non-goals

- Admin CRUD operations (will be a separate spec)
- Full-text search with relevance ranking (basic substring match is fine for v1)
- Pagination (catalog is small enough to return all results)

## Design

Three endpoints:
- `GET /api/catalog/books` — list all in-stock books
- `GET /api/catalog/books/:id` — single book by ID
- `GET /api/catalog/search?q=` — substring search on title and author

Data lives in an in-memory store for now. The schema is flat: id, title, author, price_cents, isbn, in_stock.

Price is stored in cents to avoid floating point issues.

## Links

- Belongs to: [[COMP-catalog-service]]
- Provides: [[API-CATALOG-V1]]
- Decided by: [[ADR-0001]]
- Gates: [[GATE-0001]]

## Acceptance Criteria

- [ ] GET /api/catalog/books returns all in-stock books as JSON
- [ ] GET /api/catalog/books/:id returns 404 for unknown IDs
- [ ] GET /api/catalog/search?q=design matches partial titles case-insensitively
- [ ] All responses include price_cents as an integer, never a float
- [ ] Response times under 100ms for a catalog of up to 1000 books
