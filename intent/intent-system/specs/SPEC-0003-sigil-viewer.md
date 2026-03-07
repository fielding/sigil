---
id: SPEC-0003
status: accepted
---

# Sigil Viewer

## Intent

Build a browser-based graph explorer that makes the intent graph tangible. Engineers should be able to see their entire decision landscape at a glance, drill into any node to read the full spec/ADR, and understand blast radius before making changes.

!! The viewer is the primary interface for non-CLI users. If it doesn't work well, Sigil doesn't work.

## Context

The CLI kernel ([[SPEC-0001]]) produces `graph.json` with nodes and edges. Without a visual layer, that JSON is useful only to scripts. Architects need a spatial view; new team members need a reading surface; reviewers need blast radius analysis.

>> See [[ADR-0001]] for why we chose intent-first review over traditional code review.

## Goals

- Render the full intent graph as an interactive force-directed diagram
- Click any node to read its full markdown content with proper rendering
- Show blast radius (Impact Radar) for any selected node
- Compute and display an Intent Coverage health score
- Support the human++ color scheme and annotation markers (`!!`, `??`, `>>`)
- Resolve `[[wikilinks]]` as clickable navigation within the viewer

## Non-goals

- Real-time collaboration (this is a local tool)
- Editing intent docs from the viewer (use your editor)
- Server-side rendering (static HTML + JS only)

## Design

### Architecture

Single `index.html` file with inline CSS and JS. Dependencies: D3.js (graph rendering), marked.js (markdown parsing). Loaded via CDN. No build step.

### Views

1. **Graph View** -- D3 force-directed layout. Nodes colored by type. Edge labels on hover. Zoom/pan via scroll/drag.
2. **Impact Radar** -- Concentric ring visualization. Center = selected node. Rings = direct/secondary/tertiary connections. Click to navigate.
3. **Coverage Dashboard** -- Health score (0-100%), stat cards, and actionable findings list.

### Content Panel

Right-side panel with tabs:
- **Content** -- fetches the source file, strips YAML frontmatter, renders markdown with human++ markers
- **Edges** -- lists all incoming/outgoing edges with type badges
- **Blast Radius** -- text-based impact analysis
- **Raw** -- JSON representation of the node

### Human++ Integration

?? Should we bundle the palette or fetch it from the human++ repo?

Current approach: CSS variables with hardcoded Base24 hex values from the human++ palette.json. Annotation markers (`!!`, `??`, `>>`) and keyword aliases (FIXME, TODO, NOTE) are post-processed after markdown rendering.

>> See [[ADR-0005]] for why we integrated human++.

## Links

- Belongs to: [[COMP-intent-system]]
- Depends on: [[SPEC-0001]]
- Decided by: [[ADR-0005]]

## Acceptance Criteria

- [x] Force-directed graph renders all nodes and edges from graph.json
- [x] Clicking a node shows rendered markdown content
- [x] Human++ annotation markers render as colored badges
- [x] Wikilinks navigate to the referenced node in the graph
- [x] Impact Radar shows blast radius in concentric rings
- [x] Coverage Dashboard shows health score and findings
- [x] Edge labels visible on hover
- [x] Search matches node IDs, titles, and body content
- [x] Breadcrumb navigation shows Component > Node chain
