---
id: SPEC-0002
status: proposed
---

# Bootstrapper and Demo Strategy

## Intent

Provide a way to adopt intent-first on existing projects by generating an "as-built" intent skeleton, and define a demo flow that makes the value proposition immediately visible.

## Context

Greenfield adoption is easy but rare. Most teams have existing codebases. A bootstrapper that generates components, interfaces, and spec skeletons from an existing repo removes the cold-start problem. A compelling demo sells the concept.

## Goals

- `intent bootstrap` scans a repo and generates components, interfaces, and spec skeletons
- Bootstrap output includes confidence scores on inferred relationships
- Demo flow: bootstrap -> index -> viewer -> make a change -> see graph diff in PR

## Non-goals

- Recovering true "why" from code (bootstrapper generates as-built maps, not real intent)
- Production-grade inference (heuristics are sufficient for v1)

## Design

### Bootstrap pipeline

1. **Repo scan** — discover services/packages/modules, interface files, deployment topology
2. **Dependency extraction** — regex heuristics for imports, build graph analysis
3. **Graph assembly** — create nodes and edges with confidence scores
4. **Emit skeleton intent** — spec skeletons, component registry, interface nodes
5. **Emit diagnostics** — low-confidence edges, unknown ownership, TODOs

### Demo narrative

1. "Here's the system map" (graph viewer after bootstrap)
2. "Here's an intent PR" (SPEC + ADR + interface change)
3. "Here's the graph diff review" (CI comment)
4. "Here's an implementation PR — it merges because gates pass"

## Links

- Belongs to: [[COMP-intent-system]]
- Depends on: [[SPEC-0001]]

## Acceptance Criteria

- [ ] `intent bootstrap` produces valid components/*.yaml from repo structure
- [ ] Bootstrap detects interface artifacts (OpenAPI, protobuf, JSON Schema)
- [ ] Inferred edges include confidence scores and evidence
- [ ] DEMO.md walks through the full narrative
