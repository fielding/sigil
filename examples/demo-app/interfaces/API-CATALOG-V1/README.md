---
id: API-CATALOG-V1
type: api
status: active
---

# Catalog API

## Description

REST API for browsing and searching the book catalog. Read-only. Used by the web app to render product pages and search results, and by the cart/order services to validate book IDs and look up prices.

## Contract

### `GET /api/catalog/books`

Returns all in-stock books.

```json
[
  {
    "id": "b-001",
    "title": "Designing Data-Intensive Applications",
    "author": "Martin Kleppmann",
    "price_cents": 4500,
    "isbn": "978-1449373320",
    "in_stock": true
  }
]
```

### `GET /api/catalog/books/:id`

Returns a single book by ID. 404 if not found.

### `GET /api/catalog/search?q=:query`

Full-text search across title and author.

## Links

- Provided by: [[COMP-catalog-service]]
- Consumed by: [[COMP-web-app]] [[COMP-cart-service]] [[COMP-order-service]]
- Gates: [[GATE-0001]]
