# Sigil

**Intent-first engineering. Your decisions, structured, connected, and enforced.**

Sigil makes the *why* behind your code as navigable as the code itself. Specs, ADRs, gates, and component definitions live in your repo, versioned with your code, connected in a knowledge graph, and enforced in CI.

## Why

Every team has intent scattered across Notion, Confluence, Slack threads, PR descriptions, and people's heads. When you need to know *why* a decision was made, you're left grepping through months of messages.

Sigil gives intent a home:
- **Structured** -- specs, ADRs, and gates follow templates with frontmatter
- **Connected** -- wikilinks and typed edges build a navigable knowledge graph
- **Enforced** -- gates block PRs that violate your own stated intent
- **Versioned** -- everything is in Git, reviewed like code

## Quick Start

```bash
# Install
pip install pyyaml

# Initialize in your repo
python3 tools/intent/sigil.py init

# That's it. Browser opens with your intent graph.
```

`sigil init` scans your repo, creates the directory structure, builds the knowledge graph, and opens the interactive viewer.

## The Viewer

Seven views into your intent architecture:

| View | What it shows |
|------|--------------|
| **Graph** | Force-directed knowledge graph. Drag, zoom, click to explore. |
| **Impact Radar** | Select any node, see its blast radius in concentric rings. |
| **Hierarchy** | Layered view: Components > Specs/Gates > ADRs |
| **Coverage** | Health score (0-100%) based on spec coverage, ADR maturity, reference integrity |
| **Drift** | Where your code and intent have diverged |
| **Timeline** | Git-backed history of how your intent evolved |
| **Matrix** | Dependency heatmap of node-to-node relationships |

**Command palette**: `Cmd+K` to search nodes, switch views, or create new docs.

**Keyboard navigation**: `j`/`k` cycle nodes, `/` search, `g`/`r`/`h`/`c`/`d`/`t`/`m` switch views.

**Live reload**: `sigil serve` auto-refreshes the viewer when intent docs change. Look for the green LIVE indicator.

**Human++** themed with the [Base24 color scheme](https://fielding.github.io/human-plus-plus/) and annotation markers (`!!` attention, `??` uncertainty, `>>` reference).

## CLI

```
sigil index      Build the knowledge graph from your repo
sigil status     Terminal dashboard with health bar and stats
sigil lint       Check intent docs for issues
sigil check      Run gate enforcement
sigil drift      Compare intent graph against actual code
sigil review     Analyze git diff for intent coverage
sigil suggest    Show which intent docs govern a file
sigil ask        Search intent docs with natural language
sigil timeline   Build evolution history from git log
sigil new        Create a new spec or ADR from template
sigil diff       Compute graph changes between commits
sigil export     Generate self-contained HTML snapshot
sigil badge      Generate coverage badge SVG for your README
sigil serve      Dev server with live reload
sigil init       Zero-to-working setup
sigil fmt        Normalize intent doc formatting
sigil bootstrap  Scan repo for missing component stubs
```

## Repo Structure

```
components/          Component registry (YAML)
intent/              Specs and ADRs organized by component
  {component}/
    specs/           What we're building and why
    adrs/            Architectural decisions
interfaces/          API and event contracts
gates/               Enforceable constraints
templates/           Scaffolding for new docs
.intent/             Generated artifacts (graph.json, badge, exports)
```

## CI Integration

Add to your GitHub Actions workflow:

```yaml
- run: python tools/intent/sigil.py index
- run: python tools/intent/sigil.py lint
- run: python tools/intent/sigil.py check
- run: python tools/intent/sigil.py drift || true
```

PRs get an automatic intent report comment with node/edge counts, graph diff, and coverage stats.

## Node Types

| Type | Prefix | Purpose |
|------|--------|---------|
| Component | `COMP-` | Service or module with ownership and path patterns |
| Spec | `SPEC-` | What we're building: intent, constraints, acceptance criteria |
| ADR | `ADR-` | Why we decided something: context, options, decision |
| Gate | `GATE-` | Enforceable constraint tied to components |
| Interface | `API-`/`EVT-` | API contracts and event schemas |

## Edge Types

`belongs_to` `decided_by` `depends_on` `gated_by` `provides` `consumes` `relates_to` `supersedes`

## License

MIT
