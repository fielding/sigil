---
id: SPEC-0006
status: accepted
---

# CI Pipeline Spec

The Sigil CI workflow runs on every pull request and produces a comprehensive intent report.

## Intent

Intent drift happens silently. Without enforcement, teams write intent docs once and never update them. CI integration makes intent a living part of the development workflow.

## Pipeline Steps

1. `sigil index` -- build the knowledge graph
2. `sigil lint` -- check docs for structural issues
3. `sigil check` -- enforce gates
4. `sigil drift` -- compare intent vs code
5. `sigil timeline` -- build evolution history
6. `sigil badge` -- generate coverage badge
7. `sigil export` -- create self-contained HTML snapshot
8. `sigil diff` -- compute graph changes between PR base and head

## PR Comment

The workflow posts a comment with:
- Stats table (nodes, edges, specs, ADRs, gates)
- Graph diff showing what changed

## Acceptance Criteria

- [ ] Workflow runs on PR open, sync, and reopen
- [ ] All artifacts uploaded (graph.json, diff.json, badge.svg, export.html, drift.json, timeline.json)
- [ ] PR comment includes stats table and diff
- [ ] Gate failures block merge (when configured)

## Links

- Belongs to: [[COMP-sigil-ci]]
- Depends on: [[API-INTENT-CLI-V1]]
