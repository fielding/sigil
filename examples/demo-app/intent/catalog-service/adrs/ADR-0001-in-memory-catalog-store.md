---
id: ADR-0001
status: accepted
---

# Use in-memory store for the book catalog

## Context

The catalog service needs a data store. Options range from a real database (Postgres, SQLite) to a flat file to an in-memory dict. This is a demo app with a handful of books, not a production bookstore.

## Decision

Use a Python dictionary as the data store. Books are defined as dataclass instances in the source code.

## Alternatives

- **SQLite**: Would add realism but also adds setup steps, migrations, and a dependency. Not worth it for a demo that's showing off the intent layer, not the data layer.
- **JSON file**: Slightly more realistic than in-memory, but adds file I/O concerns for no real benefit at this scale.
- **Postgres**: Way too heavy. Would require Docker Compose or a cloud database just to browse 3 books.

## Consequences

- The catalog resets on every restart. That's fine — it's a demo.
- No migration story. If we need to change the book schema, we just edit the Python code.
- Can't demonstrate database-related gates (migration safety, schema drift). That's a tradeoff we accept.
- Easy to swap out later — the API contract stays the same regardless of the backing store.

## Links

- For: [[SPEC-0001]]
