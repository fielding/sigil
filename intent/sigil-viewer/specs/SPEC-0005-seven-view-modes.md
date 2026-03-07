---
id: SPEC-0005
status: accepted
---

# Seven View Modes

The Sigil viewer provides seven distinct visualizations of the intent graph, each optimized for a different analysis task.

## Intent

Architects and developers need multiple lenses to understand a system's intent structure. A single graph view is not enough -- you need to see topology, hierarchy, coverage, drift, history, and coupling.

## Views

1. **Graph** -- force-directed knowledge graph with drag, zoom, glow effects on high-connectivity nodes, colored edges by type, and curved paths with directional arrows
2. **Impact Radar** -- concentric ring visualization showing blast radius from any selected node
3. **Hierarchy** -- layered view with components at top, specs/gates in middle, ADRs at bottom
4. **Coverage** -- health dashboard with weighted scoring (component coverage, ADR maturity, spec quality, reference integrity)
5. **Drift** -- comparison of intent graph against actual codebase file structure
6. **Timeline** -- swim-lane visualization of intent evolution from git history
7. **Matrix** -- dependency grid showing node-to-node relationships as a heatmap

## Acceptance Criteria

- [ ] All seven views render without errors
- [ ] Each view has a keyboard shortcut (g/r/h/c/d/t/m)
- [ ] Views are accessible from command palette (Cmd+K)
- [ ] View state persists across node selections

## Links

- Belongs to: [[COMP-sigil-viewer]]
- Depends on: [[API-INTENT-CLI-V1]]
- Decided by: [[ADR-0005]]
