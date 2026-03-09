# Sigil

**Your codebase knows *what*. Sigil knows *why*.**

Every team writes specs and ADRs. Almost none survive first contact with the codebase — they rot in Notion, drift from reality, and nobody reviews them in PRs. When someone asks "why was this built this way?" the answer is in a Slack thread from six months ago, or it left with the engineer who quit.

Sigil fixes this. It's a CLI that turns your specs, decisions, and constraints into a connected knowledge graph — right in your Git repo. When you open a PR, Sigil posts an intent diff: what architectural decisions changed, what specs were affected, what gates apply. Your team reviews *intent* first, code second.

**[See a live demo](https://fielding.github.io/sigil/)** — a full intent graph you can explore in your browser right now.

[![Sigil intent graph viewer — 36 nodes, 96 edges, 8 interactive views](docs/branding/graph-screenshot.png)](https://fielding.github.io/sigil/)

## See it work

```bash
$ sigil why src/services/auth.ts
src/services/auth.ts
  └─ COMP-auth-service (component)
       ├─ SPEC-0012 "Token refresh flow" (spec)
       ├─ ADR-0003 "Use JWT with short-lived tokens" (decision)
       └─ GATE-0001 "Auth token expiry check" (gate)
```

Ask "why does this file exist?" and get a real answer — traced through specs, decisions, and constraints.

```bash
$ sigil impact COMP-order-service
COMP-order-service
  Ring 1: SPEC-0003, ADR-0002, GATE-0002, API-ORDERS-V1
  Ring 2: COMP-payment-gateway, COMP-inventory, COMP-notification
  Ring 3: SPEC-0008, ADR-0005, GATE-0005
  Total: 32 affected nodes
```

Check the blast radius before you touch anything. Know what breaks.

## Concepts in 30 seconds

Sigil tracks five things. That's it.

| What | In plain English | Example |
|------|-----------------|---------|
| **Component** | A service or module in your system | `auth-service`, `payment-gateway` |
| **Spec** | The plan for what you're building and why | "Token refresh flow" — intent, constraints, acceptance criteria |
| **Decision** (ADR) | Why you chose one approach over another | "Use JWT with short-lived tokens" — context, options, outcome |
| **Gate** | A rule that must pass before code ships | "Auth tokens must expire within 1 hour" — enforced in CI |
| **Interface** | An API contract or event schema | `API-ORDERS-V1` — the surface area between services |

These connect into a graph with typed edges (`depends_on`, `gated_by`, `decided_by`, ...). That graph is what makes everything queryable, diffable, and visible.

## Install

```bash
pip install sigil-cli
sigil init
```

One command. Scans your repo, scaffolds the structure, detects components from package manifests, builds the knowledge graph, and opens an interactive viewer. Zero config.

Requires Python 3.11+.

<details>
<summary>Other install methods</summary>

```bash
# Via npx (no install required)
npx @fielding/sigil init

# Global install via npm
npm install -g @fielding/sigil

# From source
git clone https://github.com/fielding/sigil.git
cd sigil && pip install -e .
```

</details>

## Try it on a demo project

Want to see Sigil on a real (sample) codebase before using it on your own? The repo includes a complete example — a bookstore app with 9 components, 36 nodes, and 96 edges:

```bash
git clone https://github.com/fielding/sigil.git
cd sigil
pip install sigil-cli
sigil serve --repo examples/demo-app
```

Opens in your browser. Click around the graph. Try the [Impact Radar](https://fielding.github.io/sigil/) view. Check coverage. Explore drift.

## What you get

**Structure.** Specs, decisions, gates, and interfaces follow templates with typed frontmatter. Intent lives next to code, not in a wiki nobody checks.

**Connections.** Everything links. Ask `sigil why src/auth.ts` and trace from file to component to spec to decision. Ask `sigil ask "payment processing"` and search your architecture like a knowledge base.

**Enforcement.** Gates block PRs that violate your stated intent. Pattern checks, coverage thresholds, lint rules — defined in YAML, enforced in CI with `sigil ci`.

**Visibility.** Eight interactive views in a bundled browser UI:

| View | Key | Shows |
|------|-----|-------|
| **Graph** | `g` | Force-directed knowledge graph |
| **Impact Radar** | `r` | Blast radius of any node |
| **Hierarchy** | `h` | Components → Specs/Gates → Decisions |
| **Coverage** | `c` | Health score (0–100%) |
| **Drift** | `d` | Where code and intent have diverged |
| **Timeline** | `t` | Git-backed intent evolution |
| **Matrix** | `m` | Dependency heatmap |
| **Review** | `w` | Governance snapshot |

Command palette (`Cmd+K`), keyboard nav (`j`/`k`, `/` to search), live reload via `sigil serve`.

## Workflow

```bash
# Create your first spec
sigil new spec auth-service "Token refresh flow"

# Record an architectural decision
sigil new adr auth-service "Use JWT with short-lived tokens"

# Define a gate to enforce it
sigil new gate "Auth token expiry" --applies-to COMP-auth-service

# Check everything passes
sigil check

# See your intent graph health
sigil status
```

## CI Integration

Three lines in your GitHub Actions workflow:

```yaml
- run: pip install sigil-cli
- run: sigil ci
- run: sigil pr ${{ github.event.pull_request.number }}
  if: github.event_name == 'pull_request'
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

`sigil ci` runs index, lint, check, badge, and review in one shot. `sigil pr` posts a comment on your PR with coverage percentage, governed vs. ungoverned changes, gate results, and links to the intent graph. Add `--strict` to fail on warnings.

## What reviewers see

When Sigil runs on a PR, it posts a comment like this:

---

> ## Sigil Intent Analysis
>
> | Metric | Value |
> |--------|-------|
> | Intent Coverage | 🟢 **87%** (7/8 files) |
> | Intent Docs Changed | 2 |
> | Graph Nodes | 42 |
> | Graph Edges | 98 |
> | Gates | 🟢 4/4 passing |
>
> <details><summary>Intent Documents Changed</summary>
>
> - `intent/auth-service/specs/SPEC-0012.md`
> - `intent/auth-service/adrs/ADR-0003.md`
>
> </details>
>
> <details><summary>Governed Code Changes</summary>
>
> **Auth Service** (`COMP-auth-service`)
> - `src/services/auth.ts`
> - `src/middleware/jwt.ts`
> > Specs: `SPEC-0012` [accepted] | ADRs: `ADR-0003` [accepted] | Gates: `GATE-0001`
>
> **Order Service** (`COMP-order-service`)
> - `src/services/orders.ts`
> - `src/models/order.ts`
> - `src/routes/orders.ts`
> > Specs: `SPEC-0003` [accepted] | ADRs: `ADR-0002` [accepted] | Gates: `GATE-0002`
>
> </details>
>
> <details><summary>⚠️ Ungoverned Changes (1 files)</summary>
>
> These files are not mapped to any component. Run `sigil suggest <path>` for recommendations.
>
> - `src/utils/helpers.ts`
>
> </details>
>
> <details><summary>Gate Results</summary>
>
> - ✅ **GATE-0001**: Auth token expiry check passed
> - ✅ **GATE-0002**: Order validation gate passed
> - ✅ **GATE-0003**: Payment gateway interface check passed
> - ✅ **GATE-0004**: Inventory sync coverage passed
>
> </details>
>
> ---
> *Generated by [Sigil](https://fielding.github.io/sigil/) — intent-first engineering*

---

At a glance, reviewers know: which specs govern the changed code, whether any architectural decisions were updated, which gates passed, and which files aren't tracked yet. That last part is the most important — every ungoverned file is a gap in your team's institutional knowledge.

## CLI Reference

The commands you'll use most:

```
sigil init         Scaffold, index, open viewer — zero to working
sigil status       Terminal dashboard with health bar and stats
sigil serve        Dev server with live reload
sigil check        Run gate enforcement
sigil drift        Find where code and intent have diverged
sigil review       Analyze git diff for intent coverage
sigil why          Trace the full intent chain for any file
sigil ask          Search intent docs with natural language
sigil impact       Show blast radius of a node
sigil ci           Full CI pipeline in one command
sigil pr           Post intent analysis to a GitHub PR
```

Full command reference with all flags and examples: [docs/CLI.md](docs/CLI.md).

<details>
<summary>All commands</summary>

| Command | Description |
|---------|-------------|
| `init` | Zero-to-working setup: scaffold, index, and open viewer |
| `index` | Build the knowledge graph from your repo |
| `status` | Terminal dashboard with health bar and stats |
| `serve` | Dev server with file watching and auto-rebuild |
| `new` | Create a new spec, ADR, component, gate, or interface |
| `lint` | Check intent docs for structural issues |
| `fmt` | Normalize intent doc formatting |
| `bootstrap` | Scan repo and create missing component stubs |
| `scan` | Deep-scan: detect components, APIs, decisions, infra |
| `diff` | Compute graph changes between commits |
| `drift` | Compare intent graph against actual code |
| `check` | Run gate enforcement checks |
| `review` | Analyze git diff for intent coverage |
| `suggest` | Show which intent docs govern a file |
| `ask` | Search intent docs with natural language |
| `why` | Trace why a file exists through the intent chain |
| `map` | Terminal-rendered dependency map |
| `impact` | Show blast radius of a node in the graph |
| `timeline` | Build evolution history from git log |
| `export` | Generate self-contained HTML snapshot |
| `badge` | Generate coverage badge SVG |
| `hook` | Install/uninstall git pre-commit hook |
| `pr` | Analyze GitHub PR and post intent coverage comment |
| `doctor` | Diagnose installation and repo health |
| `ci` | Full CI pipeline in one command |
| `watch` | Watch intent files and re-index on change |

</details>

## Repo Structure

After `sigil init`:

```
components/          What your system is made of (YAML)
intent/              Why it's built this way
  {component}/
    specs/           Plans: what we're building and constraints
    adrs/            Decisions: why we chose this approach
    rollouts/        How we're shipping it
interfaces/          Contracts between services
gates/               Rules that must pass before code ships
templates/           Scaffolding for new docs
.intent/             Generated artifacts (gitignored)
```

## VS Code Extension

Available in `tools/sigil-vscode/` with intent graph integration, inline diagnostics, and CodeLens for intent links.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and contribution guidelines.

## License

MIT
