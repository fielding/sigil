# Sigil CLI Reference

Complete reference for every `sigil` command, flag, and option.

```
sigil [--repo REPO] [--version] COMMAND [OPTIONS]
```

**Global options:**

| Flag | Description |
|------|-------------|
| `--repo REPO` | Repo root directory (default: current working directory) |
| `--version` | Print version and exit |
| `-h, --help` | Show help |

---

## Getting Started

### `sigil init`

Zero-to-working setup. Scaffolds directories, creates config, runs bootstrap and index, then opens the viewer in your browser.

```bash
sigil init [--port PORT]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `8787` | Port for the local viewer server |

**What it does:**
1. Creates `components/`, `intent/`, `interfaces/`, `gates/`, `templates/` directories
2. Writes `.intent/config.yaml` with project defaults
3. Copies document templates into `templates/`
4. Runs `bootstrap` to detect existing components
5. Runs `index` to build the knowledge graph
6. Opens the interactive viewer at `http://localhost:PORT`

### `sigil bootstrap`

Scans your repo for package manifests (`package.json`, `setup.py`, `Cargo.toml`, etc.) and creates component YAML stubs for anything not already registered.

```bash
sigil bootstrap [--dry-run]
```

| Flag | Description |
|------|-------------|
| `--dry-run` | Print what would be created without writing files |

### `sigil new`

Create a new intent document from a template.

```bash
sigil new {spec,adr,component,gate,interface} NAME [TITLE] [--applies-to NODES]
```

| Argument | Description |
|----------|-------------|
| `type` | One of: `spec`, `adr`, `component`, `gate`, `interface` |
| `name` | Component slug (for spec/adr/component), interface ID (for interface), or title (for gate) |
| `title` | Document title (required for spec, adr, interface, gate) |

| Flag | Description |
|------|-------------|
| `--applies-to` | Comma-separated node IDs the gate applies to (gate type only) |

**Examples:**

```bash
sigil new spec auth-service "Token refresh flow"
sigil new adr auth-service "Use JWT with short-lived tokens"
sigil new component payment-gateway
sigil new gate "No secrets in code" --applies-to COMP-api-server,COMP-auth-service
sigil new interface API-ORDERS-V1 "Orders REST API"
```

### `sigil doctor`

Diagnose your Sigil installation and repo health. Checks Python version, dependencies, directory structure, config validity, and index freshness.

```bash
sigil doctor
```

---

## Everyday Use

### `sigil status`

Terminal dashboard showing intent graph health: node/edge counts, coverage score, health bar, and gate results.

```bash
sigil status [--json]
```

| Flag | Description |
|------|-------------|
| `--json` | Output as JSON for scripting |

### `sigil check`

Run all gate enforcement checks. Gates are defined in `gates/GATE-XXXX-*.yaml` and can be pattern checks, lint rules, commands, or coverage thresholds.

```bash
sigil check [--json] [--watch] [--interval SECONDS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--json` | | Output as JSON |
| `--watch` | | Re-run checks on file changes (continuous mode) |
| `--interval` | `2` | Poll interval in seconds for `--watch` |

**Gate types:**

- **`pattern`** — Glob + regex match (with optional negation). Checks that files matching a pattern do/don't contain a regex.
- **`command`** — Runs an arbitrary shell command. Exit 0 = pass.
- **`lint-rule`** — Built-in structural checks on intent documents.
- **`threshold`** — Coverage score must meet a minimum value.

### `sigil lint`

Check intent documents for structural issues: missing frontmatter fields, broken wikilinks, invalid IDs, formatting problems.

```bash
sigil lint [--min-severity {error,warn,info}]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--min-severity` | `warn` | Minimum severity to report |

### `sigil fmt`

Normalize intent document formatting. Auto-assigns IDs to documents missing them, and ensures Links sections are consistent.

```bash
sigil fmt
```

### `sigil serve`

Start a development server that watches for file changes and auto-rebuilds the graph. Opens the interactive viewer with live reload.

```bash
sigil serve [--port PORT]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `8787` | Server port |

### `sigil watch`

Watch intent files and re-index the graph on every change. Lighter than `serve` — no HTTP server, just file watching and rebuild.

```bash
sigil watch [--interval SECONDS] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--interval` | `2` | Poll interval in seconds |
| `--json` | | Output JSON summaries on each rebuild |

---

## Exploration

### `sigil ask`

Search intent docs with a natural-language question. Uses fuzzy matching with section-aware ranking (IDs and titles weighted higher than body text).

```bash
sigil ask QUESTION [--top N] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--top` | `5` | Number of results to return |
| `--json` | | Output as JSON |

**Example:**

```bash
sigil ask "how does authentication work?"
sigil ask "payment retry logic" --top 3
```

### `sigil why`

Trace why a file exists by walking the intent chain. Shows which components own the file, their specs, ADRs, and gates.

```bash
sigil why PATH
```

**Example:**

```bash
sigil why src/services/auth.ts
```

### `sigil suggest`

Show which intent docs govern a file. Similar to `why` but focused on coverage — useful for understanding if a file has intent backing.

```bash
sigil suggest PATH
```

### `sigil map`

Render a dependency map of the intent graph in the terminal. Three display modes for different views of the graph structure.

```bash
sigil map [--mode {tree,deps,flat}] [--focus NODE]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | `tree` | `tree`: hierarchical, `deps`: dependency chains, `flat`: sorted list |
| `--focus` | | Focus on a specific node or component |

**Example:**

```bash
sigil map
sigil map --mode deps --focus COMP-auth-service
```

### `sigil impact`

Show the blast radius of a node — everything that could be affected by a change, organized in concentric rings by distance.

```bash
sigil impact NODE [--depth N] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--depth` | `3` | Max traversal depth |
| `--json` | | Output as JSON |

**Example:**

```bash
sigil impact COMP-order-service
sigil impact auth --depth 5
```

Node lookup is flexible: exact ID, case-insensitive match, prefix match, or substring search.

---

## Analysis

### `sigil coverage`

Show intent coverage report with a health score (0–100). Scores are weighted across four metrics: components with specs (40%), ADRs accepted (30%), specs with acceptance criteria (20%), and no dangling references (10%).

```bash
sigil coverage [--json]
```

| Flag | Description |
|------|-------------|
| `--json` | Output as JSON |

Per-component breakdown: green (has spec + ADR), yellow (has one), red (has neither).

### `sigil drift`

Detect drift between the intent graph and the actual codebase. Finds files that have changed since their governing intent docs were last updated.

```bash
sigil drift
```

### `sigil review`

Analyze a git diff for intent coverage. Shows which changed files are governed by intent docs and which are not.

```bash
sigil review [BASE] [HEAD] [--staged] [--json]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `base` | `HEAD` | Base commit |
| `head` | working tree | Head commit |

| Flag | Description |
|------|-------------|
| `--staged` | Review staged changes only |
| `--json` | Output as JSON |

**Example:**

```bash
sigil review                      # Review working tree changes
sigil review HEAD~3 HEAD          # Review last 3 commits
sigil review --staged             # Review what's about to be committed
sigil review main feature-branch  # Review branch diff
```

### `sigil scan`

Deep-scan the codebase for components, APIs, architectural decisions, and infrastructure patterns. Produces a report of findings that can be used to bootstrap intent docs.

```bash
sigil scan [--dry-run] [--output PATH]
```

| Flag | Description |
|------|-------------|
| `--dry-run` | Print findings without writing the report |
| `-o, --output` | Output path for scan report JSON |

### `sigil diff`

Compute the graph diff between two commits. Shows added, removed, and modified nodes and edges.

```bash
sigil diff BASE HEAD [--out PATH] [--md PATH]
```

| Argument | Description |
|----------|-------------|
| `base` | Base commit SHA |
| `head` | Head commit SHA |

| Flag | Description |
|------|-------------|
| `--out` | Output diff as JSON |
| `--md` | Output diff as Markdown |

### `sigil timeline`

Build a timeline of intent evolution from git history. Scans commits for changes to intent documents and produces a chronological record.

```bash
sigil timeline [--max N] [--output PATH]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--max` | `50` | Maximum number of commits to scan |
| `-o, --output` | `.intent/index/timeline.json` | Output path |

---

## CI / Integration

### `sigil ci`

Run the full CI pipeline in one command: index → lint → check → badge → review. Designed for CI environments.

```bash
sigil ci [BASE] [HEAD] [--strict]
```

| Argument | Description |
|----------|-------------|
| `base` | Base commit for review (optional) |
| `head` | Head commit for review (optional) |

| Flag | Description |
|------|-------------|
| `--strict` | Exit non-zero on any warnings (not just errors) |

### `sigil pr`

Analyze a GitHub PR and post an intent coverage comment. Shows coverage percentage, governed vs. ungoverned files, gate results, and graph links.

```bash
sigil pr [NUMBER] [--dry-run]
```

| Argument | Description |
|----------|-------------|
| `number` | PR number (default: detects from current branch) |

| Flag | Description |
|------|-------------|
| `--dry-run` | Print comment body without posting to GitHub |

Requires `GITHUB_TOKEN` environment variable for posting.

### `sigil hook`

Install or uninstall the Sigil git pre-commit hook. When installed, runs `sigil lint` before every commit.

```bash
sigil hook {install,uninstall,status}
```

### `sigil badge`

Generate an SVG coverage badge for your README or dashboard.

```bash
sigil badge [--output PATH]
```

| Flag | Default | Description |
|------|---------|-------------|
| `-o, --output` | `.intent/badge.svg` | Output path |

### `sigil export`

Generate a self-contained HTML snapshot of the intent graph viewer. The exported file includes all graph data embedded — no server needed.

```bash
sigil export [--output PATH]
```

| Flag | Default | Description |
|------|---------|-------------|
| `-o, --output` | `.intent/export.html` | Output path |

### `sigil index`

Build the knowledge graph from your repo. Parses all intent documents, resolves links, and writes `graph.json` and derived artifacts to `.intent/index/`.

```bash
sigil index
```

This is run automatically by `init`, `ci`, and `serve`. You typically only need to run it manually after bulk-editing intent docs outside of `serve` mode.
