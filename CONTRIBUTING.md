# Contributing to Sigil

Thanks for your interest in contributing to Sigil. This guide covers setup, testing, and conventions.

## Development Setup

```bash
git clone https://github.com/fielding/sigil.git
cd sigil
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Or without the editable install:

```bash
pip install pyyaml pytest
```

The CLI lives at `tools/intent/sigil.py`. You can run it directly:

```bash
python3 tools/intent/sigil.py --help
```

Or via the installed entry point after `pip install -e .`:

```bash
sigil --help
```

## Project Layout

```
tools/intent/sigil.py        CLI source (single-file until it outgrows ~1000 lines)
tools/intent/tests/           Test suite
tools/intent_viewer/          Browser-based graph viewer (HTML/JS/D3)
tools/sigil-vscode/           VS Code extension
templates/                    Document templates (SPEC.md, ADR.md, etc.)
examples/demo-app/            Full working example project
docs/                         Documentation
```

## Running Tests

```bash
pytest tools/intent/tests/
```

To run a specific test file:

```bash
pytest tools/intent/tests/test_integration.py -v
```

## Architecture

Sigil is intentionally simple:

- **Single file CLI.** `sigil.py` contains all commands, the graph builder, gate runner, and output formatters. We'll split when it outgrows maintainability, not before.
- **Minimal dependencies.** PyYAML is the only required dependency. No frameworks, no ORMs, no plugin systems.
- **Repo-native.** All data lives in the repo as Markdown and YAML. Generated artifacts go under `.intent/index/` (gitignored). No external databases or services.
- **Graph-first.** Everything is a node or an edge. Components, specs, ADRs, gates, interfaces — they're all nodes connected by typed edges. Commands operate on this graph.

## Writing a New Command

1. Add a `cmd_yourcommand(args, repo)` function in `sigil.py`
2. Register it in the argument parser setup (find the `subparsers` block)
3. Add it to the appropriate workflow group in the help output
4. Write tests in `tools/intent/tests/test_yourcommand.py`

Commands receive the parsed `args` namespace and `repo` path. Use existing helpers:

- `_load_graph(repo)` — parse all intent docs, return the graph dict
- `_load_config(repo)` — load `.intent/config.yaml`
- `_resolve_node_id(query, g)` — fuzzy node lookup
- `_compute_coverage(repo, g)` — health score calculation

## Writing Tests

Tests use pytest with `tmp_path` fixtures for isolated repo scaffolding. See existing tests for patterns:

```python
def test_something(tmp_path):
    # Set up a minimal repo structure
    (tmp_path / "components").mkdir()
    comp = tmp_path / "components" / "foo.yaml"
    comp.write_text("id: COMP-foo\nname: Foo\nowner: team-a\npaths:\n  - src/foo/\n")

    # Run CLI or call internal functions
    result = subprocess.run(
        ["python3", "tools/intent/sigil.py", "--repo", str(tmp_path), "status"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
```

## Intent Documents

Sigil uses its own framework. Intent docs for the Sigil project itself live under `intent/intent-system/`. Read those to understand the conventions:

- **Specs** have frontmatter with `id`, `title`, `status`, `component`, and sections for Context, Intent, Constraints, and Acceptance Criteria.
- **ADRs** have `status` (proposed/accepted/deprecated/superseded), Context, Options, Decision, and Consequences.
- **Gates** are YAML with `id`, `summary`, `kind`, `policy`, `on_fail`, and type-specific fields.
- **Components** are YAML with `id`, `name`, `owner`, `paths`, and optional `depends_on`.

Use `sigil new` to generate correctly-formatted documents from templates.

## Code Style

- Python 3.11+ features are welcome
- No type stubs or mypy required, but type hints on public functions are appreciated
- Keep functions focused — if a function is doing three things, split it
- Error messages should be actionable: tell the user what went wrong and what to do about it

## Pull Requests

1. Create a feature branch from `main`
2. Make your changes and add tests
3. Run `pytest tools/intent/tests/` and ensure all tests pass
4. Run `sigil ci --repo examples/demo-app` to verify against the demo project
5. Open a PR with a clear description of what and why

## Reporting Issues

Open an issue at [github.com/fielding/sigil/issues](https://github.com/fielding/sigil/issues). Include:

- What you expected vs. what happened
- Sigil version (`sigil --version`)
- Python version
- Minimal reproduction steps if possible
