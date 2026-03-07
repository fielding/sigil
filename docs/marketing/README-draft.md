# Sigil

**Review intent, not just diffs.**

Sigil is an open-source CLI that turns your specs, ADRs, and architectural constraints into a knowledge graph — in your Git repo. When you open a PR, Sigil posts an intent diff showing what architectural decisions changed, so your team reviews intent first and code second.

<!-- Consider adding: ![Intent Coverage](https://img.shields.io/badge/intent_coverage-87%25-brightgreen) -->

```
$ sigil init
Bootstrapped 3 components from manifest files.
Indexed 12 nodes, 18 edges.
Viewer running at http://localhost:8787
```

---

## Why Sigil

Every team writes specs. Almost none survive first contact with the codebase. They rot in Notion, drift from reality, and nobody reviews them in PRs.

Sigil fixes this by making intent:

- **Visible** — Interactive graph viewer shows your system's architecture as connected nodes
- **Reviewable** — CI posts intent diffs on every PR, so architectural changes get reviewed alongside code
- **Structured** — Components, specs, ADRs, interfaces, and gates live in your repo with typed relationships
- **Enforceable** — Gate constraints (coming soon) verify code conforms to stated intent

## Quick Demo

### 1. Initialize your repo

```bash
pip install pyyaml
sigil init
```

Sigil creates a structured directory layout, auto-discovers your components from manifest files (package.json, pyproject.toml, go.mod, etc.), builds an index, and opens the interactive viewer.

### 2. Write a spec

```bash
sigil new spec user-service "Authentication flow redesign"
```

Creates `intent/user-service/specs/SPEC-0003-authentication-flow-redesign.md` from a template with sections for Intent, Goals, Non-goals, Design, and Acceptance Criteria.

### 3. See the graph

```bash
sigil index
# Open the viewer
python -m http.server 8787 --directory tools/intent_viewer
```

The interactive D3 viewer renders your system as a force-directed graph: components, specs, ADRs, interfaces, and gates connected by typed edges.

### 4. Review intent in PRs

Add the GitHub Actions workflow (`.github/workflows/intent.yml`), and every PR gets a comment like:

```markdown
## Intent Diff: main..feature/auth-redesign

### Nodes changed
- SPEC-0003 (added): Authentication flow redesign
- API-AUTH-V2 (changed): Updated token endpoint contract

### Edges changed
- SPEC-0003 --belongs_to--> COMP-user-service (added)
- SPEC-0003 --gated_by--> GATE-0002 (added)

### Summary
2 nodes added/changed, 2 edges added. 0 removed.
```

## Key Features

### Knowledge Graph
Sigil indexes your intent artifacts into a graph with typed nodes and edges. Components `provides` interfaces. Specs are `decided_by` ADRs. Gates `constrain` interfaces. The graph is queryable, diffable, and visualizable.

### Graph Diff
`sigil diff base..head` computes structural changes to your intent graph across commits. What specs were added? What interfaces changed? What constraints apply? CI posts this as a PR comment automatically.

### Lint and Format
`sigil lint` validates your intent documents: required front matter, required sections, valid status values, no dangling references. `sigil fmt` normalizes documents in-place.

### Bootstrap
`sigil bootstrap` auto-discovers components from your repo's manifest files and creates component registry entries. Get from zero to indexed in one command.

### Interactive Viewer
A static D3 force graph explorer with search, filtering, and detail panels. No build step. No server. Just HTML and your graph.json.

## Node Types

| Type | Prefix | Description |
|---|---|---|
| Component | `COMP-*` | Service, package, or module in your system |
| Spec | `SPEC-*` | Intent plan: what you're building and why |
| Decision | `ADR-*` | Architectural decision record |
| Interface | `API-*`, `EVT-*` | Contract definition (API, event, schema) |
| Gate | `GATE-*` | Enforceable constraint tied to intent |

## Edge Types

`belongs_to` | `decided_by` | `provides` | `consumes` | `depends_on` | `gated_by` | `supersedes` | `relates_to`

## Repo Structure

```
your-repo/
  components/          # Component registry (YAML)
  intent/
    <component>/
      specs/           # Specifications (SPEC-*)
      adrs/            # Decisions (ADR-*)
  interfaces/          # API/event contracts
  gates/               # Constraint definitions
  templates/           # Scaffolding templates
  .intent/
    config.yaml        # Sigil configuration
    index/
      graph.json       # Generated knowledge graph
      search.json      # Search index
```

## CI Integration

Add the included GitHub Actions workflow to get intent diffs on every PR:

```yaml
# .github/workflows/intent.yml
name: Intent Diff
on: [pull_request]
jobs:
  intent-diff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install pyyaml
      - run: python tools/intent/sigil.py index
      - run: python tools/intent/sigil.py lint
      - run: python tools/intent/sigil.py diff ${{ github.event.pull_request.base.sha }} ${{ github.event.pull_request.head.sha }} --md .intent/index/diff.md
      - uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const body = fs.readFileSync('.intent/index/diff.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
```

<!-- ## Intent Coverage Badge

Track what percentage of your codebase is covered by intent artifacts:

```markdown
![Intent Coverage](https://img.shields.io/badge/intent_coverage-87%25-brightgreen)
```

Intent coverage = (components with at least one linked spec or ADR) / (total components). Sigil can generate this metric from your graph. Badge integration coming soon. -->

## Requirements

- Python 3.11+
- PyYAML (`pip install pyyaml`)
- That's it.

## Roadmap

- [x] Repo schema and conventions
- [x] CLI: index, diff, new, lint, fmt, bootstrap, init
- [x] Knowledge graph with typed nodes and edges
- [x] Interactive D3 viewer
- [x] GitHub Actions CI integration
- [ ] VS Code extension (autocomplete, quick fixes, inline graph)
- [ ] Gate enforcement engine
- [ ] Intent coverage metrics and badges
- [ ] Drift detection (code changes without intent updates)

## Philosophy

Sigil is built on three beliefs:

1. **Intent should live where code lives.** Not in Notion, not in Confluence, not in someone's head. In Git, versioned, diffable, reviewable.

2. **Architecture should be a first-class review surface.** If your CI checks types and tests, it should also check intent. The plan matters as much as the implementation.

3. **Tools should be simple.** One Python file. One dependency. No platform to deploy. No account to create. Clone the repo and run `sigil init`.

## License

MIT
