---
id: ADR-0006
status: accepted
---

# Use Next.js for the storefront frontend

## Context

We need a web frontend for the bookstore. The catalog pages benefit from server-side rendering (fast first paint, SEO), while the cart needs client-side interactivity. We want a framework that handles both without a complex build setup.

## Decision

Use Next.js with the App Router. Server components for catalog pages, client components for cart interactions.

## Alternatives

- **Plain React (Create React App / Vite)**: Simpler, but no SSR. Catalog pages would show a loading spinner while fetching books. Not a great first impression.
- **Remix**: Also does SSR well, but smaller ecosystem and less familiar to most developers. Next.js is the safer bet for a demo that people need to understand quickly.
- **Static site + API**: Pre-render catalog at build time. Works for a fixed inventory, but doesn't demonstrate real-time data fetching.
- **No frontend (API only)**: Would simplify the demo but make it less compelling. People want to see a UI.

## Consequences

- Need Node.js in addition to Python for the backend services. Adds to the tech stack.
- Server components can call backend APIs directly, reducing client-side JavaScript.
- The frontend is a thin layer — no business logic, just API calls and rendering.
- The app/ directory follows Next.js conventions, which is well-documented.

## Links

- For: [[SPEC-0006]]
