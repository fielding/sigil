# Sigil

**Your codebase knows *what*. Sigil knows *why*.**

Sigil is an intent graph framework for software projects. Specs, ADRs, gates, and component definitions live in your repo — versioned with your code, connected in a navigable knowledge graph, and enforced in CI. No SaaS, no sync, no drift between your docs and your code.

**[Live Demo](https://fielding.github.io/sigil/)** — explore a full intent graph in your browser.

## Quick Start

```bash
pip install sigil-cli

cd your-project
sigil init
```

`sigil init` scans your repo, scaffolds the directory structure, detects components from package manifests, builds the knowledge graph, and opens an interactive viewer. One command, zero config.

## What You Get

**Structure.** Specs, ADRs, gates, and interfaces follow templates with typed frontmatter. No more intent buried in Notion pages and Slack threads.

**Connections.** Wikilinks and typed edges (`depends_on`, `gated_by`, `decided_by`, ...) build a graph you can query, visualize, and diff. Ask "why does this file exist?" and get an answer: `sigil why src/auth.ts`.

**Enforcement.** Gates block PRs that violate your own stated intent. Pattern checks, coverage thresholds, lint rules — all defined in YAML, all run in CI with `sigil ci`.

**Visibility.** Eight interactive views in a bundled browser UI:

| View | Key | What it shows |
|------|-----|--------------|
| **Graph** | `g` | Force-directed knowledge graph — drag, zoom, click |
| **Impact Radar** | `r` | Blast radius of any node in concentric rings |
| **Hierarchy** | `h` | Layered: Components → Specs/Gates → ADRs |
| **Coverage** | `c` | Health score (0–100%) across specs, ADRs, references |
| **Drift** | `d` | Where code and intent have diverged |
| **Timeline** | `t` | Git-backed evolution of your intent |
| **Matrix** | `m` | Dependency heatmap across all nodes |
| **Review** | `w` | Governance snapshot: coverage, gates, drift |

Command palette (`Cmd+K`), keyboard nav (`j`/`k`, `/` to search), and live reload via `sigil serve`.

## CLI Reference

The ones you'll use most:

```
sigil init         Zero-to-working setup: scaffold, index, open viewer
sigil status       Terminal dashboard with health bar and stats
sigil serve        Dev server with live reload
sigil check        Run gate enforcement
sigil drift        Find where code and intent have diverged
sigil review       Analyze git diff for intent coverage
sigil why          Trace the full intent chain for any file
sigil ask          Search intent docs with natural language
sigil ci           Full CI pipeline: index + lint + check + badge + review
sigil pr           Post intent coverage analysis to a GitHub PR
```

<details>
<summary>Full command list</summary>

| Command | Description |
|---------|-------------|
| `init` | Zero-to-working setup: scaffold, index, and open viewer |
| `index` | Build the knowledge graph from your repo |
| `status` | Terminal dashboard with health bar and stats |
| `serve` | Dev server with file watching and auto-rebuild |
| `new` | Create a new spec or ADR from template |
| `lint` | Check intent docs for structural issues |
| `fmt` | Normalize intent doc formatting (IDs, links) |
| `bootstrap` | Scan repo and create missing component stubs |
| `scan` | Deep-scan: detect components, APIs, decisions, infra |
| `diff` | Compute graph changes between commits |
| `drift` | Compare intent graph against actual code |
| `check` | Run gate enforcement checks |
| `review` | Analyze git diff for intent coverage |
| `suggest` | Show which intent docs govern a file |
| `ask` | Search intent docs with natural language |
| `why` | Trace why a file exists through the intent chain |
| `map` | Terminal-rendered dependency map (tree, deps, flat) |
| `timeline` | Build evolution history from git log |
| `export` | Generate self-contained HTML snapshot |
| `badge` | Generate coverage badge SVG |
| `hook` | Install/uninstall git pre-commit hook |
| `pr` | Analyze GitHub PR and post intent coverage comment |
| `doctor` | Diagnose installation and repo health |
| `ci` | Full CI pipeline in one command |

</details>

## CI Integration

```yaml
- run: sigil ci
- run: sigil pr ${{ github.event.pull_request.number }}
```

`sigil ci` runs index → lint → check → badge → review in one shot. Add `--strict` to fail on warnings.

PRs get an automatic comment with coverage percentage, governed vs. ungoverned changes, gate results, and links to the intent graph.

## Repo Structure

```
components/          Component registry (YAML)
intent/              Specs and ADRs, organized by component
  {component}/
    specs/           What we're building and why
    adrs/            Architectural decisions
interfaces/          API and event contracts
gates/               Enforceable constraints (YAML)
templates/           Scaffolding for new docs
.intent/             Generated artifacts (graph.json, badge, exports)
```

## Node Types

| Type | Prefix | Purpose |
|------|--------|---------|
| Component | `COMP-` | Service or module with ownership and path patterns |
| Spec | `SPEC-` | What we're building: intent, constraints, acceptance criteria |
| ADR | `ADR-` | Why we decided something: context, options, decision |
| Gate | `GATE-` | Enforceable constraint tied to components |
| Interface | `API-`/`EVT-` | API contracts and event schemas |

## Edge Types

`belongs_to` · `decided_by` · `depends_on` · `gated_by` · `provides` · `consumes` · `relates_to` · `supersedes`

## License

MIT
