---
id: SPEC-0006
status: accepted
---

# Storefront UI

## Intent

Give users a web interface to browse books, manage their cart, and check out. The frontend is a thin layer over the backend APIs — it shouldn't contain business logic.

## Context

We need a frontend. Next.js gives us server-side rendering for the catalog pages (good for SEO and initial load) and client-side interactivity for the cart. The UI is deliberately minimal — this is a Sigil demo, not a design showcase.

## Goals

- Product listing page showing all books
- Individual book detail page
- Cart sidebar with add/remove/quantity
- Checkout button that calls the orders API
- Login/register forms
- Order history page

## Non-goals

- Responsive design polish
- Accessibility audit (would be important in production)
- Client-side search (server-side is fine)
- Animations or transitions

## Design

Pages map directly to API endpoints:

- `/` — home, links to catalog
- `/catalog` — calls [[API-CATALOG-V1]], renders book grid
- `/catalog/:id` — book detail page
- `/cart` — reads [[API-CART-V1]], add/remove controls
- `/checkout` — calls [[API-ORDERS-V1]] checkout endpoint
- `/orders` — calls [[API-ORDERS-V1]] list endpoint
- `/login`, `/register` — calls [[API-AUTH-V1]]

Auth state is stored in a cookie. All API calls include the JWT token.

## Links

- Belongs to: [[COMP-web-app]]
- Consumes: [[API-CATALOG-V1]] [[API-AUTH-V1]] [[API-CART-V1]] [[API-ORDERS-V1]]
- Depends on: [[COMP-catalog-service]] [[COMP-auth-service]] [[COMP-cart-service]] [[COMP-order-service]]
- Decided by: [[ADR-0006]]

## Acceptance Criteria

- [ ] Catalog page renders book titles, authors, and prices
- [ ] Adding a book from catalog updates the cart count
- [ ] Cart page shows all items with quantities and a checkout button
- [ ] Checkout redirects to order confirmation
- [ ] Unauthenticated users are redirected to login
