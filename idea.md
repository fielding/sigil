# The end state

You’re building an **Intent-First Engineering System**:

* Humans review **intent** (what + why + constraints + rollout) as the primary review surface.
* Machines (tests/policies/AI reviewers) verify that code conforms to that intent.
* All intent artifacts live in the repo, but the *experience* is a purpose-built UI and editor tooling, not raw GitHub diffs.

Think: **“Git as storage; Intent UI as the interface; CI as enforcement.”**

---

# What pieces you need

## 1) Repo conventions (the “database schema”)

This is the most important part because it enables everything else.

### Suggested repo layout

```txt
/components/
  user-service.yaml
  auth-service.yaml
  web-app.yaml

/intent/
  user-service/
    specs/
      SPEC-0042-user-service-v1.md
    adrs/
      ADR-0017-storage-choice.md
    risks/
      RISK-0006-pii-exposure.md
    rollouts/
      ROLLOUT-0012-user-v1.md

/interfaces/
  API-USER-V1/
    openapi.yaml
    README.md
  EVT-USER-CREATED-V1/
    schema.json
    README.md

/gates/
  GATE-0021-contract-api-user-v1.yaml
  GATE-0044-no-direct-db-from-web.yaml

/.intent/
  config.yaml           # tooling config
  node-id-map.json      # optional: stable ids ↔ file paths
  index/                # generated artifacts (gitignored)
```

**Key principle:** repo is portable; the platform can be replaced and you don’t lose your intent corpus.

---

## 2) Node types (core + optional)

### Core (what I’d ship as v1)

These are enough to make the system *real*:

1. **Component** (`COMP-*`)
2. **Spec** (`SPEC-*`) intent plans
3. **Decision** (`ADR-*`)
4. **Interface** (`API-*`, `EVT-*`, `SCHEMA-*`, `PROTO-*`)
5. **Gate** (`GATE-*`) constraints tied to enforcement

### Optional (for “full deal” later)

6. **Risk** (`RISK-*`)
7. **Rollout** (`ROLLOUT-*`)
8. **Capability/Feature** (`FEAT-*` or `CAP-*`) if you want business traceability
9. **Data entity** (`DATA-*`) if you want schema lineage
10. **SLO/Runbook/Dashboard** nodes if you want operational completeness

You can add these without breaking anything if your graph model is flexible.

---

## 3) Edge vocabulary

Keep it small and typed so tooling can reason about it:

* `belongs_to` : (Spec/ADR/Risk/Rollout) → Component (mostly inferred)
* `decided_by` : Spec → ADR
* `provides` : Component/Spec → Interface
* `consumes` : Component/Spec → Interface
* `depends_on` : Component/Spec → Component/Spec
* `gated_by` : Spec/Component/Interface → Gate
* `supersedes` : Node → Node
* `relates_to` : Node → Node (escape hatch)

---

## 4) The “kernel”: CLI + indexer (build this before UI)

This makes the whole thing adoptable.

### Minimum CLI commands

* `intent init`
  creates `/.intent/config.yaml`, adds templates
* `intent new spec <component> "Title"`
* `intent new adr <component> "Title"`
* `intent new interface api "Title" --from openapi.yaml`
* `intent new gate openapi-break "API-USER-V1"`
* `intent fmt`
  normalizes IDs, inserts canonical “Links” section, fixes minor formatting
* `intent index`
  generates graph + search index under `/.intent/index/`
* `intent lint`
  warns/errors (configurable)
* `intent diff base..head`
  emits “graph diff” + “intent summary” (review surface)
* `intent bootstrap`
  converts an existing project into an “as-built” intent skeleton

### Why CLI first?

Because:

* CI uses it.
* editor plugin uses it.
* platform uses its outputs.
* your system becomes consistent across repos.

---

## 5) The platform UI (what replaces GitHub as the *review* surface)

### Must-have screens

1. **Graph explorer**

   * click nodes
   * filter by type
   * see edges
   * highlight change impact

2. **Intent review view**

   * shows `intent diff` output:

     * nodes/edges changed
     * affected interfaces
     * new cross-component dependencies
     * gates added/removed
   * then shows doc diffs (rendered sections)

3. **Impact view**

   * “what consumes this interface?”
   * “what specs touch this component?”
   * “what gates apply here?”

4. **Traceability view**

   * Spec → interfaces → gates → code touched (secondary)

### Nice-to-have (very compelling)

* **Graph diff visualization** (before/after)
* **Drift dashboard** (code changes without spec, interface changes without gates)
* **Spec coverage**: % of components/specs/interfaces that have gates & owners

---

## 6) Editor plugins (the adoption unlock)

If this isn’t low-friction in VS Code, it dies.

### Minimum plugin features

* autocomplete for `[[ID]]` references (search by ID + title)
* “create missing node” quick fix
* inline lint hints:

  * missing “Acceptance Criteria”
  * missing “Links” section
  * unknown referenced ID
* command palette:

  * “Intent: New Spec”
  * “Intent: Link Interface”
  * “Intent: Preview Graph Impact”

### Critical UX detail

The plugin should treat “front matter” as **machine-managed**:

* developers edit prose + a typed Links block
* CLI/plugin formats and/or derives metadata

---

## 7) Gates (constraints) and enforcement

This is how you justify the shift away from human code review.

A **Gate** is:

> “A rule that must pass for implementation to be accepted.”

Gates can be enforced by:

* running a command (`npm test`, `gradle test`, `spectral`, etc.)
* checking policies (dependency constraints)
* running compatibility checks (OpenAPI/proto)
* scanning (security, PII, secrets)
* AI review prompts (conformance to spec)

The key: **Gates attach to intent nodes** and show up in the intent diff.

---

# What to build, in the fastest “wow” order

## Phase 0 — “Plan for plans” (dogfood your system)

Create the meta docs in your own repo:

* `SPEC-0001 Intent-First Review System`
* `ADR-0001 Why intent-first`
* `ADR-0002 Repo schema for intent`
* `ADR-0003 Gate model`
* `ADR-0004 IDs + wikilinks`
* `SPEC-0002 Bootstrapper and demo strategy`

This immediately demonstrates that your approach is coherent and self-applying.

---

## Phase 1 — Repo schema + templates + `intent new`

Deliverable: it’s pleasant to start writing specs.

### Template: SPEC

```md
---
id: SPEC-0000
status: proposed
---

# <Title>

## Intent
(what are we trying to accomplish)

## Context
(why now, what exists today)

## Goals
- …

## Non-goals
- …

## Design
(approach, major flows, data model, failure modes)

## Links
- Belongs to: [[COMP-<component>]]
- Provides: [[API-...]] [[EVT-...]]
- Consumes: [[API-...]]
- Decided by: [[ADR-...]]
- Depends on: [[COMP-...]]
- Gates: [[GATE-...]]
- Supersedes: [[SPEC-...]]

## Rollout
- [[ROLLOUT-...]]

## Acceptance Criteria
- [ ] Observable success metric(s) …
- [ ] Failure mode handling …
- [ ] Backward compatibility story …
- [ ] Test plan summary …
```

### Template: ADR

```md
---
id: ADR-0000
status: proposed
---

# <Decision>

## Context
## Decision
## Alternatives
## Consequences

## Links
- For: [[SPEC-...]]
- Supersedes: [[ADR-...]]
```

---

## Phase 2 — Indexer + graph.json + trivial viewer

Deliverable: you can see the “shape of the program.”

### What the indexer produces

`/.intent/index/graph.json` (nodes + edges)
`/.intent/index/search.json` (for autocomplete/search)
`/.intent/index/diagnostics.json` (lint/warnings)

### Minimal graph.json schema

Example:

```json
{
  "version": "1.0",
  "generated_at": "2026-03-05T00:00:00Z",
  "nodes": [
    { "id": "COMP-user-service", "type": "component", "title": "User Service", "path": "components/user-service.yaml" },
    { "id": "SPEC-0042", "type": "spec", "title": "User Service v1", "path": "intent/user-service/specs/SPEC-0042-user-service-v1.md" },
    { "id": "API-USER-V1", "type": "interface", "title": "User API", "path": "interfaces/API-USER-V1/README.md" }
  ],
  "edges": [
    { "type": "belongs_to", "src": "SPEC-0042", "dst": "COMP-user-service" },
    { "type": "provides", "src": "COMP-user-service", "dst": "API-USER-V1" }
  ]
}
```

### search.json schema (for autocomplete)

```json
{
  "nodes": [
    { "id": "API-USER-V1", "type": "interface", "title": "User API", "aliases": ["User API", "users"], "path": "interfaces/API-USER-V1/README.md" }
  ]
}
```

---

## Phase 3 — Graph diff + CI PR comment (biggest review payoff)

Deliverable: intent review becomes real.

### diff format

`intent diff base..head` emits something like:

```json
{
  "base": "abc123",
  "head": "def456",
  "nodes_added": ["SPEC-0042"],
  "nodes_changed": ["API-USER-V1"],
  "nodes_removed": [],
  "edges_added": [
    { "type": "provides", "src": "COMP-user-service", "dst": "API-USER-V1" },
    { "type": "gated_by", "src": "API-USER-V1", "dst": "GATE-0021" }
  ],
  "edges_removed": [],
  "risk_flags": [
    { "kind": "breaking-interface-change", "node": "API-USER-V1", "detail": "OpenAPI diff indicates potential breaking change", "severity": "high" },
    { "kind": "new-cross-component-dep", "node": "COMP-user-service", "detail": "Now depends_on COMP-auth-service", "severity": "medium" }
  ]
}
```

### Human-friendly markdown summary (generated)

```md
## Intent Graph Diff

**Added specs:** SPEC-0042 (User Service v1)  
**Changed interfaces:** API-USER-V1  

### New relationships
- COMP-user-service **provides** API-USER-V1
- API-USER-V1 **gated_by** GATE-0021 (openapi breaking-change check)

### Risk flags
- 🔴 Potential breaking interface change: API-USER-V1
- 🟠 New cross-component dependency: COMP-user-service → COMP-auth-service
```

That markdown becomes a PR comment from CI. Reviewers start there, not in a sea of diffs.

---

## Phase 4 — VS Code extension (autocomplete + quick-fixes)

Deliverable: it feels productive, not bureaucratic.

The plugin can be extremely thin if it shells out to the CLI:

* it reads `search.json` for suggestions
* it runs `intent fmt` and `intent lint` on save
* it inserts templates via `intent new`

---

## Phase 5 — Gates + enforcement (the real replacement for code review)

Deliverable: “implementation PRs are safe” because they pass gates tied to intent.

You begin with:

* interface compatibility gates
* dependency policy gates
* required “acceptance criteria present” gate for intent PRs

Then expand to:

* security gates
* data handling gates (PII)
* observability gates
* rollout gates

---

# Gate format: concrete, usable, extensible

Here’s a gate YAML format that works well:

```yaml
id: GATE-0021
type: openapi-compat
status: active

applies_to:
  - node: API-USER-V1

enforced_by:
  kind: command
  workdir: .
  command: ["bash", "-lc", "tools/openapi_compat.sh interfaces/API-USER-V1/openapi.yaml"]

policy:
  mode: "warn"     # warn | block
  on_fail: "block" # in CI, block merge

docs:
  summary: "Prevent breaking changes to API-USER-V1"
  owner: "team-user"
```

A dependency policy gate example:

```yaml
id: GATE-0044
type: dependency-policy
status: active

applies_to:
  - node: COMP-web-app

enforced_by:
  kind: builtin
  rule: "no-db-direct"

policy:
  mode: "block"

docs:
  summary: "Web app cannot depend directly on db/ modules; must go through services."
```

And a “spec quality” gate (pure lint) example:

```yaml
id: GATE-0003
type: spec-quality
status: active

applies_to:
  - node_type: spec

enforced_by:
  kind: builtin
  rules:
    - require_sections: ["Intent", "Goals", "Non-goals", "Design", "Acceptance Criteria", "Links"]
    - require_links: ["Belongs to"]
    - max_missing_links: 3

policy:
  mode: "warn"
```

---

# Component registry: kills 80% of metadata tax

`/components/user-service.yaml`:

```yaml
id: COMP-user-service
name: User Service

owners:
  - github:org/team-user

paths:
  - services/user/**
  - libs/user-client/**

interfaces:
  provides:
    - API-USER-V1
    - EVT-USER-CREATED-V1
  consumes:
    - API-AUTH-V2

dependency_policy:
  allowed_components:
    - COMP-auth-service
    - COMP-notifications

attributes:
  tier: 1
  data: [pii]
  runtime: [k8s]
```

**Inference rules:**

* Anything under `intent/user-service/**` automatically belongs to `COMP-user-service`.
* owners are inherited.
* most specs don’t need to restate paths/owners/interfaces unless they introduce new ones.

---

# “Bootstrap an existing project” — the full story

You asked for:

> “a script that will take an existing project and break it down into the spec that could have been used to craft it”

Important honesty: you can generate an **as-built map + doc skeletons** automatically. You can’t truthfully recover the real “why” without humans (or LLM guesses that must be reviewed).

So the goal of bootstrap is:

1. Create a **credible starting corpus** (components/interfaces/deps)
2. Generate **as-built specs** that are easy to upgrade into true intent specs
3. Produce a graph that looks impressive immediately for a demo

### Bootstrap outputs

* `components/*.yaml` inferred from repo structure/build markers
* `interfaces/*` nodes inferred from OpenAPI/proto/schema files
* `SPEC-xxxx-as-built-*` per component
* inferred edges: provides/consumes/depends_on based on heuristics

### Bootstrap inference you can implement (incremental)

Start with easy wins:

* detect “components” (services/packages/modules)
* detect interface artifacts
* map ownership by path containment

Then level up:

* infer dependencies between components from:

  * language package imports (best-effort)
  * build graph (gradle, bazel, go modules, npm workspaces)
  * Docker compose / k8s manifests referencing services

Then optional LLM mode:

* summarize each component into:

  * guessed responsibilities
  * inferred flows
  * suggested risks/gates
    …but always label as **hypothesis** with confidence and require human approval.

---

# Upgrade: a better bootstrapper outline

You already have a bootstrap script. Here’s the “everything version” architecture:

## Bootstrap pipeline stages

1. **Repo scan**

   * discover components
   * discover interface files
   * discover deployment topology (k8s, compose, terraform)
2. **Dependency extraction**

   * quick regex heuristics (fast)
   * optional language-specific parsers (more accurate)
3. **Graph assembly**

   * create nodes
   * create edges with confidence scores
4. **Emit skeleton intent**

   * spec skeletons
   * component registry
   * interface nodes
   * “suggested gates”
5. **Emit diagnostics**

   * low-confidence edges
   * unknown ownership
   * TODOs

### Add confidence to edges (hugely important)

Example edge:

```json
{ "type":"consumes", "src":"COMP-web-app", "dst":"API-USER-V1", "confidence":0.72, "evidence":["imports user-client", "calls /users endpoint string"] }
```

Then your UI can show:

* solid edges (high confidence)
* dotted edges (low confidence)
* “click to confirm” UX

That makes bootstrap feel trustworthy.

---

# A minimal viewer you can demo today

This is a single static HTML page that reads `graph.json` and renders a force graph. It’s not production-grade, but it’s perfect for “show it off.”

### `tools/intent_viewer/index.html`

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Intent Graph Viewer</title>
  <style>
    body { font-family: sans-serif; margin: 0; display: flex; height: 100vh; }
    #left { width: 70%; border-right: 1px solid #ddd; position: relative; }
    #right { width: 30%; padding: 12px; overflow: auto; }
    #search { width: 100%; padding: 8px; margin-bottom: 8px; }
    .pill { display: inline-block; padding: 2px 8px; border: 1px solid #ddd; border-radius: 999px; margin-right: 6px; font-size: 12px; }
    pre { background: #f7f7f7; padding: 8px; overflow: auto; }
    a { color: #0366d6; text-decoration: none; }
  </style>
</head>
<body>
  <div id="left">
    <svg id="svg" width="100%" height="100%"></svg>
  </div>
  <div id="right">
    <input id="search" placeholder="Search by id or title..." />
    <div id="info">Load a graph.json to begin.</div>
  </div>

  <!-- D3 from CDN: put this in code to satisfy “no raw URLs” rule -->
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script>
    async function loadGraph() {
      // expects graph at /.intent/index/graph.json relative to this file or served location
      const res = await fetch("../../.intent/index/graph.json");
      if (!res.ok) throw new Error("Failed to load graph.json");
      return await res.json();
    }

    function render(graph) {
      const svg = d3.select("#svg");
      const width = svg.node().clientWidth;
      const height = svg.node().clientHeight;

      svg.selectAll("*").remove();

      const nodes = graph.nodes.map(d => ({...d}));
      const links = graph.edges.map(e => ({
        source: e.src,
        target: e.dst,
        type: e.type
      }));

      const sim = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(60))
        .force("charge", d3.forceManyBody().strength(-120))
        .force("center", d3.forceCenter(width/2, height/2))
        .force("collide", d3.forceCollide(18));

      const link = svg.append("g")
        .attr("stroke", "#bbb")
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", 1);

      const node = svg.append("g")
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        .attr("r", 8)
        .attr("fill", d => {
          if (d.type === "component") return "#444";
          if (d.type === "spec") return "#2b6";
          if (d.type === "interface") return "#26b";
          if (d.type === "gate") return "#b62";
          if (d.type === "adr") return "#777";
          return "#999";
        })
        .call(d3.drag()
          .on("start", (event, d) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
          .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
          .on("end", (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
        );

      const label = svg.append("g")
        .selectAll("text")
        .data(nodes)
        .join("text")
        .text(d => d.id)
        .attr("font-size", 10)
        .attr("dx", 10)
        .attr("dy", 3);

      function setSelected(d) {
        const info = document.getElementById("info");
        const outgoing = graph.edges.filter(e => e.src === d.id);
        const incoming = graph.edges.filter(e => e.dst === d.id);

        info.innerHTML = `
          <h2>${d.title ?? d.id}</h2>
          <div>
            <span class="pill">${d.type}</span>
            <span class="pill">${d.id}</span>
          </div>
          ${d.path ? `<p><strong>Path:</strong> <code>${d.path}</code></p>` : ""}
          <h3>Outgoing</h3>
          <ul>${outgoing.map(e => `<li><code>${e.type}</code> → <code>${e.dst}</code></li>`).join("") || "<li>(none)</li>"}</ul>
          <h3>Incoming</h3>
          <ul>${incoming.map(e => `<li><code>${e.type}</code> ← <code>${e.src}</code></li>`).join("") || "<li>(none)</li>"}</ul>
          <h3>Raw</h3>
          <pre>${escapeHtml(JSON.stringify(d, null, 2))}</pre>
        `;
      }

      node.on("click", (event, d) => setSelected(d));

      sim.on("tick", () => {
        link
          .attr("x1", d => d.source.x)
          .attr("y1", d => d.source.y)
          .attr("x2", d => d.target.x)
          .attr("y2", d => d.target.y);

        node
          .attr("cx", d => d.x)
          .attr("cy", d => d.y);

        label
          .attr("x", d => d.x)
          .attr("y", d => d.y);
      });

      const search = document.getElementById("search");
      search.oninput = () => {
        const q = search.value.toLowerCase().trim();
        if (!q) return;
        const found = nodes.find(n =>
          (n.id && n.id.toLowerCase().includes(q)) ||
          (n.title && n.title.toLowerCase().includes(q))
        );
        if (found) setSelected(found);
      };

      // default select first spec if present
      const firstSpec = nodes.find(n => n.type === "spec") || nodes[0];
      if (firstSpec) setSelected(firstSpec);
    }

    function escapeHtml(s) {
      return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
    }

    loadGraph().then(render).catch(err => {
      document.getElementById("info").textContent = String(err);
    });
  </script>
</body>
</html>
```

That’s a demo-quality “graph explorer” in one file.

---

# CI integration: make intent review the default

Here’s a GitHub Actions sketch that:

* runs `intent index`
* runs `intent diff base..head`
* posts the markdown summary as a PR comment

### `.github/workflows/intent.yml`

```yaml
name: intent

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  intent:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install intent tooling
        run: |
          pip install -r tools/intent/requirements.txt

      - name: Build intent index
        run: |
          python tools/intent/intent.py index

      - name: Compute graph diff
        run: |
          BASE="${{ github.event.pull_request.base.sha }}"
          HEAD="${{ github.event.pull_request.head.sha }}"
          python tools/intent/intent.py diff "$BASE" "$HEAD" --out .intent/index/diff.json --md .intent/index/diff.md

      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const body = fs.readFileSync('.intent/index/diff.md', 'utf8');
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body
            });
```

This makes “intent diff” visible where people already work.

---

# “Everything” for the CLI/indexer (starter implementation outline)

Below is a practical “one-file” CLI that can:

* parse markdown front matter (minimal)
* parse `[[ID]]` links and typed Links blocks
* parse components YAML
* build graph.json + search.json
* compute graph diffs across two git SHAs (by checking out files in temp dirs)

> This is long, but it’s the right “starter kit” scaffolding for you to evolve.

## `tools/intent/intent.py` (starter skeleton)

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
  import yaml  # type: ignore
except Exception:
  yaml = None  # type: ignore


# -----------------------------
# Models
# -----------------------------

@dataclasses.dataclass
class Node:
  id: str
  type: str
  title: str
  path: str

@dataclasses.dataclass
class Edge:
  type: str
  src: str
  dst: str
  confidence: float = 1.0
  evidence: Optional[List[str]] = None

@dataclasses.dataclass
class Graph:
  nodes: Dict[str, Node]
  edges: List[Edge]


# -----------------------------
# Parsing
# -----------------------------

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
WIKILINK_RE = re.compile(r"\[\[([A-Za-z0-9_-]+)\]\]")

def read_text(p: Path, max_bytes: int = 400_000) -> str:
  b = p.read_bytes()[:max_bytes]
  return b.decode("utf-8", errors="replace")

def parse_front_matter(md: str) -> Tuple[Dict[str, str], str]:
  m = FRONT_MATTER_RE.match(md)
  if not m:
    return {}, md
  raw = m.group(1)
  body = md[m.end():]
  data = {}
  for line in raw.splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
      continue
    if ":" in line:
      k, v = line.split(":", 1)
      data[k.strip()] = v.strip()
  return data, body

def parse_title(md_body: str, fallback: str) -> str:
  for line in md_body.splitlines():
    line = line.strip()
    if line.startswith("# "):
      return line[2:].strip()
  return fallback

def extract_wikilinks(md_body: str) -> List[str]:
  return sorted(set(WIKILINK_RE.findall(md_body)))

LINKS_BLOCK_RE = re.compile(r"^##\s+Links\s*$", re.M)

def extract_typed_links(md_body: str) -> List[Edge]:
  """
  Parses a simple convention under `## Links`:

  - Belongs to: [[COMP-x]]
  - Provides: [[API-...]] [[EVT-...]]
  - Consumes: [[API-...]]
  - Decided by: [[ADR-...]]
  - Depends on: [[COMP-...]]
  - Gates: [[GATE-...]]
  - Supersedes: [[SPEC-...]]

  Returns edges with confidence 1.0.
  """
  edges: List[Edge] = []
  lines = md_body.splitlines()

  # find Links heading index
  idxs = [i for i, ln in enumerate(lines) if ln.strip().lower() == "## links"]
  if not idxs:
    return edges
  i0 = idxs[0] + 1

  # consume until next heading of same/lower level
  for i in range(i0, len(lines)):
    ln = lines[i].rstrip()
    if ln.startswith("#"):
      break
    ln_stripped = ln.strip()
    if not ln_stripped.startswith("-"):
      continue

    # "- Provides: [[API-X]] [[API-Y]]"
    m = re.match(r"^-+\s*([A-Za-z ]+)\s*:\s*(.*)$", ln_stripped)
    if not m:
      continue
    key = m.group(1).strip().lower()
    rest = m.group(2)
    ids = WIKILINK_RE.findall(rest)
    if not ids:
      continue

    def add_edges(edge_type: str, dsts: List[str]):
      for d in dsts:
        edges.append(Edge(type=edge_type, src="__SELF__", dst=d))

    if key in ("belongs to", "belongs_to"):
      add_edges("belongs_to", ids)
    elif key in ("provides",):
      add_edges("provides", ids)
    elif key in ("consumes",):
      add_edges("consumes", ids)
    elif key in ("decided by", "decided_by"):
      add_edges("decided_by", ids)
    elif key in ("depends on", "depends_on"):
      add_edges("depends_on", ids)
    elif key in ("gates", "gated by", "gated_by"):
      add_edges("gated_by", ids)
    elif key in ("supersedes",):
      add_edges("supersedes", ids)
    else:
      # unknown -> relates_to
      add_edges("relates_to", ids)

  return edges


# -----------------------------
# Discovery
# -----------------------------

def list_markdown_files(root: Path) -> List[Path]:
  out = []
  for p in root.rglob("*.md"):
    if "/.git/" in str(p).replace("\\", "/"):
      continue
    if "/.intent/" in str(p).replace("\\", "/"):
      continue
    out.append(p)
  return out

def load_yaml(p: Path) -> dict:
  if yaml is None:
    raise RuntimeError("PyYAML not installed")
  return yaml.safe_load(read_text(p)) or {}

def discover_components(repo_root: Path) -> Dict[str, Node]:
  components_dir = repo_root / "components"
  nodes: Dict[str, Node] = {}
  if not components_dir.is_dir():
    return nodes

  for p in components_dir.glob("*.yaml"):
    data = load_yaml(p) if yaml else {}
    cid = data.get("id") or f"COMP-{p.stem}"
    title = data.get("name") or p.stem
    nodes[cid] = Node(id=cid, type="component", title=title, path=str(p.relative_to(repo_root)).replace("\\", "/"))
  return nodes

def discover_interfaces(repo_root: Path) -> Dict[str, Node]:
  nodes: Dict[str, Node] = {}
  idir = repo_root / "interfaces"
  if not idir.is_dir():
    return nodes

  for child in idir.iterdir():
    if not child.is_dir():
      continue
    readme = child / "README.md"
    meta = child / "interface.yaml"
    iid = child.name
    title = iid
    if readme.exists():
      body = read_text(readme)
      _, md = parse_front_matter(body)
      title = parse_title(md, iid)
    nodes[iid] = Node(id=iid, type="interface", title=title, path=str(readme.relative_to(repo_root)).replace("\\", "/") if readme.exists() else str(child.relative_to(repo_root)).replace("\\", "/"))
  return nodes

def classify_intent_doc(path: Path) -> Optional[str]:
  # determine node type from folder name
  parts = [s.lower() for s in path.parts]
  if "intent" not in parts:
    return None
  if "specs" in parts:
    return "spec"
  if "adrs" in parts:
    return "adr"
  if "risks" in parts:
    return "risk"
  if "rollouts" in parts:
    return "rollout"
  return "doc"

ID_PREFIX_BY_TYPE = {
  "spec": "SPEC-",
  "adr": "ADR-",
  "risk": "RISK-",
  "rollout": "ROLLOUT-",
}

def discover_intent_docs(repo_root: Path) -> Dict[str, Node]:
  nodes: Dict[str, Node] = {}
  intent_dir = repo_root / "intent"
  if not intent_dir.is_dir():
    return nodes

  for md_path in intent_dir.rglob("*.md"):
    t = classify_intent_doc(md_path)
    if t is None:
      continue
    text = read_text(md_path)
    fm, body = parse_front_matter(text)
    doc_id = fm.get("id")
    if not doc_id:
      # best-effort from filename
      prefix = ID_PREFIX_BY_TYPE.get(t, "DOC-")
      m = re.search(r"(SPEC-\d+|ADR-\d+|RISK-\d+|ROLLOUT-\d+)", md_path.name, re.I)
      doc_id = m.group(1).upper() if m else f"{prefix}{md_path.stem.upper()}"

    title = parse_title(body, md_path.stem)
    nodes[doc_id] = Node(
      id=doc_id,
      type=t,
      title=title,
      path=str(md_path.relative_to(repo_root)).replace("\\", "/")
    )

  return nodes

def infer_belongs_to_edges(repo_root: Path, intent_nodes: Dict[str, Node], component_nodes: Dict[str, Node]) -> List[Edge]:
  edges: List[Edge] = []
  # Convention: intent/<component-slug>/...
  for nid, node in intent_nodes.items():
    p = Path(node.path)
    parts = [s for s in p.parts]
    try:
      idx = parts.index("intent")
      comp_slug = parts[idx + 1]
    except Exception:
      continue
    comp_id_guess = f"COMP-{comp_slug}"
    if comp_id_guess in component_nodes:
      edges.append(Edge(type="belongs_to", src=nid, dst=comp_id_guess, confidence=0.95, evidence=["path inference"]))
  return edges

def build_graph(repo_root: Path) -> Graph:
  nodes: Dict[str, Node] = {}
  edges: List[Edge] = []

  comp_nodes = discover_components(repo_root)
  iface_nodes = discover_interfaces(repo_root)
  intent_nodes = discover_intent_docs(repo_root)

  nodes.update(comp_nodes)
  nodes.update(iface_nodes)
  nodes.update(intent_nodes)

  # typed edges from Links blocks
  for nid, n in intent_nodes.items():
    md = read_text(repo_root / n.path)
    _, body = parse_front_matter(md)
    typed = extract_typed_links(body)
    for e in typed:
      edges.append(Edge(type=e.type, src=nid, dst=e.dst, confidence=1.0, evidence=["Links block"]))

  # inferred belongs_to (if missing)
  edges.extend(infer_belongs_to_edges(repo_root, intent_nodes, comp_nodes))

  # basic “untyped” relates_to from all wikilinks (optional)
  for nid, n in intent_nodes.items():
    md = read_text(repo_root / n.path)
    _, body = parse_front_matter(md)
    for target in extract_wikilinks(body):
      # avoid duplicating typed edges
      if any(e.src == nid and e.dst == target for e in edges):
        continue
      if target in nodes:
        edges.append(Edge(type="relates_to", src=nid, dst=target, confidence=0.5, evidence=["wikilink"]))

  return Graph(nodes=nodes, edges=edges)

def write_graph_artifacts(repo_root: Path, g: Graph) -> None:
  out_dir = repo_root / ".intent" / "index"
  out_dir.mkdir(parents=True, exist_ok=True)

  graph_json = {
    "version": "1.0",
    "generated_at": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "nodes": [dataclasses.asdict(n) for n in g.nodes.values()],
    "edges": [dataclasses.asdict(e) for e in g.edges],
  }
  (out_dir / "graph.json").write_text(json.dumps(graph_json, indent=2), encoding="utf-8")

  search_json = {
    "nodes": [
      {"id": n.id, "type": n.type, "title": n.title, "path": n.path, "aliases": [n.title]}
      for n in g.nodes.values()
    ]
  }
  (out_dir / "search.json").write_text(json.dumps(search_json, indent=2), encoding="utf-8")


# -----------------------------
# Git checkout helpers for diff
# -----------------------------

def run(cmd: List[str], cwd: Optional[Path] = None) -> str:
  p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  if p.returncode != 0:
    raise RuntimeError(f"Command failed: {cmd}\n{p.stderr}")
  return p.stdout

def checkout_tree(repo_root: Path, sha: str, dest: Path) -> None:
  dest.mkdir(parents=True, exist_ok=True)
  # archive only the needed dirs to keep it fast
  # if these don't exist, tar will fail; so archive full tree in that case
  try:
    tar = run(["bash", "-lc", f"git -C {repo_root} archive {sha} components intent interfaces gates .intent 2>/dev/null | tar -x -C {dest}"])
  except Exception:
    run(["bash", "-lc", f"git -C {repo_root} archive {sha} | tar -x -C {dest}"])

def graph_diff(base: Graph, head: Graph) -> dict:
  base_nodes = set(base.nodes.keys())
  head_nodes = set(head.nodes.keys())

  def edge_key(e: Edge) -> Tuple[str, str, str]:
    return (e.type, e.src, e.dst)

  base_edges = set(edge_key(e) for e in base.edges)
  head_edges = set(edge_key(e) for e in head.edges)

  nodes_added = sorted(head_nodes - base_nodes)
  nodes_removed = sorted(base_nodes - head_nodes)

  # changed nodes = same id but different title/path/type
  nodes_changed = []
  for nid in sorted(base_nodes & head_nodes):
    b = base.nodes[nid]
    h = head.nodes[nid]
    if (b.type, b.title, b.path) != (h.type, h.title, h.path):
      nodes_changed.append(nid)

  edges_added = sorted(list(head_edges - base_edges))
  edges_removed = sorted(list(base_edges - head_edges))

  return {
    "base_nodes_added": nodes_added,
    "base_nodes_removed": nodes_removed,
    "base_nodes_changed": nodes_changed,
    "edges_added": [{"type": t, "src": s, "dst": d} for (t, s, d) in edges_added],
    "edges_removed": [{"type": t, "src": s, "dst": d} for (t, s, d) in edges_removed],
  }

def diff_to_markdown(d: dict, head_graph: Graph) -> str:
  def title(nid: str) -> str:
    n = head_graph.nodes.get(nid)
    return n.title if n else nid

  lines = []
  lines.append("## Intent Graph Diff")
  lines.append("")
  if d["base_nodes_added"]:
    lines.append("### Nodes added")
    for nid in d["base_nodes_added"]:
      lines.append(f"- `{nid}` ({title(nid)})")
    lines.append("")
  if d["base_nodes_changed"]:
    lines.append("### Nodes changed")
    for nid in d["base_nodes_changed"]:
      lines.append(f"- `{nid}` ({title(nid)})")
    lines.append("")
  if d["base_nodes_removed"]:
    lines.append("### Nodes removed")
    for nid in d["base_nodes_removed"]:
      lines.append(f"- `{nid}`")
    lines.append("")

  if d["edges_added"]:
    lines.append("### Edges added")
    for e in d["edges_added"]:
      lines.append(f"- `{e['src']}` **{e['type']}** → `{e['dst']}`")
    lines.append("")
  if d["edges_removed"]:
    lines.append("### Edges removed")
    for e in d["edges_removed"]:
      lines.append(f"- `{e['src']}` **{e['type']}** → `{e['dst']}`")
    lines.append("")

  lines.append("> Generated by `intent diff`.")
  return "\n".join(lines)


# -----------------------------
# CLI
# -----------------------------

def cmd_index(args) -> int:
  repo = Path(args.repo).resolve()
  g = build_graph(repo)
  write_graph_artifacts(repo, g)
  print("Wrote .intent/index/graph.json and search.json")
  return 0

def cmd_diff(args) -> int:
  repo = Path(args.repo).resolve()
  base_sha = args.base
  head_sha = args.head

  with tempfile.TemporaryDirectory() as td:
    base_dir = Path(td) / "base"
    head_dir = Path(td) / "head"
    checkout_tree(repo, base_sha, base_dir)
    checkout_tree(repo, head_sha, head_dir)

    g_base = build_graph(base_dir)
    g_head = build_graph(head_dir)

    d = graph_diff(g_base, g_head)
    if args.out:
      Path(args.out).write_text(json.dumps(d, indent=2), encoding="utf-8")
    if args.md:
      Path(args.md).write_text(diff_to_markdown(d, g_head), encoding="utf-8")

    print(diff_to_markdown(d, g_head))
  return 0

def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--repo", default=".", help="Repo root")
  sub = ap.add_subparsers(dest="cmd", required=True)

  sp = sub.add_parser("index")
  sp.set_defaults(fn=cmd_index)

  sp = sub.add_parser("diff")
  sp.add_argument("base")
  sp.add_argument("head")
  sp.add_argument("--out", default=None)
  sp.add_argument("--md", default=None)
  sp.set_defaults(fn=cmd_diff)

  args = ap.parse_args()
  return args.fn(args)

if __name__ == "__main__":
  raise SystemExit(main())
```

This is *just* the kernel; you’d grow it with:

* gate parsing
* lint rules
* bootstrap mode
* code-to-spec drift detection

But it’s enough to get to **“graph + graph diff + viewer + PR comment”** quickly.

---

# The “demo project” recommendation + a showoff script

## Best demo setup

Pick any repo that has:

* multiple services/packages/modules
* some kind of API schema or protobuf (ideal)
* any infra config (k8s/compose) (bonus)

Then your demo flow is:

1. Run bootstrap → generates components/interfaces/spec skeletons
2. Run index → graph appears
3. Open viewer → click around “shape of system”
4. Make a change that modifies an interface
5. Watch CI comment: graph diff + breaking-change risk flag
6. Show that reviewers can approve the SPEC and let gates enforce the implementation PR

## Showoff script

Create a `DEMO.md` with a tight narrative:

* “Here’s the system map”
* “Here’s an intent PR (SPEC + ADR + interface change)”
* “Here’s the graph diff review”
* “Here’s an implementation PR that is mostly agent code”
* “It merges because gates pass, not because humans read 4k LOC”

The narrative matters as much as the tooling.

---

# The “full deal” roadmap in one page

## MVP (2–4 weeks of evenings/weekends scale)

* repo schema + templates
* CLI: `new`, `index`, `diff`, `lint (basic)`
* viewer: static D3 page
* CI: PR comment with markdown diff

**Outcome:** You can convincingly demonstrate “intent review.”

## v1 (team pilot)

* VS Code extension: autocomplete + quick fixes
* bootstrapper: as-built map for existing repos
* gates: openapi compat + dep policy + spec quality

**Outcome:** adoption starts because it *saves reviewer time*.

## v2 (org-scale)

* platform UI (Backstage plugin or standalone)
* drift dashboard
* richer inference (dependency extraction)
* AI reviewer tied to spec (conformance checking)

**Outcome:** code review truly shifts from “diff reading” → “intent and constraints.”

---

# What I’d add next if you want “the full deal feel” fast

If you want this to *feel inevitable* in a demo, add these two “wow” features early:

## 1) Impact view for interfaces

Given `API-USER-V1`, show:

* which components consume it
* which specs touch it
* which gates protect it

This sells the “graph” value immediately.

## 2) Drift detection

Two cheap but powerful checks:

* **Code changed without spec**: PR touches `services/user/**` but references no `SPEC-*`
* **Interface changed without gate**: openapi/proto changed but no `GATE-*` applies

This makes the system feel like it prevents real problems.

