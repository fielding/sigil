---
id: ADR-0001
status: accepted
---

# Why Intent-First

## Context

Traditional code review focuses on diffs — line-by-line implementation details. At scale, this fails: reviewers lack context, rubber-stamp approvals, and miss architectural issues. Meanwhile, AI can generate code faster than humans can review it.

## Decision

Adopt an intent-first model where the primary review surface is structured intent documents (specs, ADRs, interface definitions) rather than code diffs. Implementation review is delegated to automated gates and AI conformance checks.

## Alternatives

1. **Status quo (diff review)** — doesn't scale with AI-generated code velocity
2. **PR templates / checklists** — lightweight but unstructured, no enforcement
3. **Architecture-as-code tools (Backstage, etc.)** — catalog-focused, not review-focused

## Consequences

- Higher upfront cost: teams must write specs before (or alongside) implementation
- Lower review cost: reviewers read intent, not diffs
- Better traceability: every change links back to a spec and its constraints
- Requires tooling investment: CLI, editor plugin, CI integration

## Links

- For: [[SPEC-0001]]
