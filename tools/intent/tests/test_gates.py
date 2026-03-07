"""Tests for gate enforcement: lint-rule, command, pattern, and threshold gates."""
import sys
import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": ".", "json": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _setup_repo(tmp_path):
    """Create minimal repo structure for gate tests."""
    (tmp_path / "components").mkdir()
    (tmp_path / "intent" / "mycomp" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "mycomp" / "adrs").mkdir(parents=True)
    (tmp_path / "interfaces").mkdir()
    (tmp_path / "gates").mkdir()
    (tmp_path / ".intent").mkdir()

    # Component
    (tmp_path / "components" / "mycomp.yaml").write_text(
        "id: COMP-mycomp\ntitle: My Component\npaths:\n  - src/**\n",
        encoding="utf-8",
    )

    # Spec with acceptance criteria and status
    (tmp_path / "intent" / "mycomp" / "specs" / "SPEC-0001-foo.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Foo\n\n## Intent\nTest.\n\n## Acceptance Criteria\n\n- Works\n\n## Links\n\n- Belongs to: [[COMP-mycomp]]\n",
        encoding="utf-8",
    )

    # ADR with status
    (tmp_path / "intent" / "mycomp" / "adrs" / "ADR-0001-bar.md").write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# Bar\n\n## Context\nTest.\n\n## Decision\nOk.\n\n## Links\n\n- For: [[SPEC-0001]]\n",
        encoding="utf-8",
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Lint-rule gates
# ---------------------------------------------------------------------------

def test_lint_rule_gate_passes(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "gates" / "GATE-0001-spec-quality.yaml").write_text(
        "id: GATE-0001\ntype: spec-quality\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: lint-rule\n  checks:\n    - all_specs_have_acceptance_criteria\n    - all_specs_have_status\npolicy:\n  on_fail: block\n",
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 0


def test_lint_rule_gate_fails_missing_acceptance_criteria(tmp_path):
    repo = _setup_repo(tmp_path)
    # Overwrite spec without acceptance criteria
    (repo / "intent" / "mycomp" / "specs" / "SPEC-0001-foo.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Foo\n\n## Intent\nTest.\n\n## Links\n\n- Belongs to: [[COMP-mycomp]]\n",
        encoding="utf-8",
    )
    (repo / "gates" / "GATE-0001-spec-quality.yaml").write_text(
        "id: GATE-0001\ntype: spec-quality\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: lint-rule\n  checks:\n    - all_specs_have_acceptance_criteria\npolicy:\n  on_fail: block\n",
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 1


def test_lint_rule_gate_warn_policy_does_not_fail(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "intent" / "mycomp" / "specs" / "SPEC-0001-foo.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Foo\n\n## Intent\nTest.\n\n## Links\n\n- Belongs to: [[COMP-mycomp]]\n",
        encoding="utf-8",
    )
    (repo / "gates" / "GATE-0001-spec-quality.yaml").write_text(
        "id: GATE-0001\ntype: spec-quality\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: lint-rule\n  checks:\n    - all_specs_have_acceptance_criteria\npolicy:\n  on_fail: warn\n",
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 0  # warn policy -> does not fail


def test_lint_rule_missing_status(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "intent" / "mycomp" / "specs" / "SPEC-0001-foo.md").write_text(
        "---\nid: SPEC-0001\n---\n\n# Foo\n\n## Acceptance Criteria\n\n- Works\n\n## Links\n\n- Belongs to: [[COMP-mycomp]]\n",
        encoding="utf-8",
    )
    (repo / "gates" / "GATE-0001.yaml").write_text(
        "id: GATE-0001\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: lint-rule\n  checks:\n    - all_specs_have_status\npolicy:\n  on_fail: block\n",
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 1


def test_lint_rule_adr_status(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "intent" / "mycomp" / "adrs" / "ADR-0001-bar.md").write_text(
        "---\nid: ADR-0001\n---\n\n# Bar\n\n## Context\nTest.\n\n## Links\n\n- For: [[SPEC-0001]]\n",
        encoding="utf-8",
    )
    (repo / "gates" / "GATE-0002.yaml").write_text(
        "id: GATE-0002\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: lint-rule\n  checks:\n    - all_adrs_have_status\npolicy:\n  on_fail: block\n",
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 1


def test_inactive_gate_is_skipped(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "gates" / "GATE-0001.yaml").write_text(
        "id: GATE-0001\nstatus: inactive\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: lint-rule\n  checks:\n    - all_specs_have_acceptance_criteria\npolicy:\n  on_fail: block\n",
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 0


# ---------------------------------------------------------------------------
# Command gates
# ---------------------------------------------------------------------------

def test_command_gate_passes(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "gates" / "GATE-CMD.yaml").write_text(
        'id: GATE-CMD\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: command\n  command: ["true"]\npolicy:\n  on_fail: block\ndocs:\n  summary: "Always passes"\n',
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 0


def test_command_gate_fails(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "gates" / "GATE-CMD.yaml").write_text(
        'id: GATE-CMD\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: command\n  command: ["false"]\npolicy:\n  on_fail: block\ndocs:\n  summary: "Always fails"\n',
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 1


def test_command_gate_with_workdir(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "src").mkdir()
    (repo / "src" / "check.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (repo / "src" / "check.sh").chmod(0o755)
    (repo / "gates" / "GATE-CMD.yaml").write_text(
        'id: GATE-CMD\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: command\n  command: ["./check.sh"]\n  workdir: src\npolicy:\n  on_fail: block\n',
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 0


# ---------------------------------------------------------------------------
# Pattern gates
# ---------------------------------------------------------------------------

def test_pattern_gate_forbidden_match_fails(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("import db\nfrom db import connect\n", encoding="utf-8")

    (repo / "gates" / "GATE-PAT.yaml").write_text(
        'id: GATE-PAT\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: pattern\n  patterns:\n    - glob: "src/**/*.py"\n      regex: "import db"\n      label: "direct db import"\npolicy:\n  on_fail: block\ndocs:\n  summary: "No direct db imports"\n',
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 1


def test_pattern_gate_no_match_passes(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("import os\n", encoding="utf-8")

    (repo / "gates" / "GATE-PAT.yaml").write_text(
        'id: GATE-PAT\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: pattern\n  patterns:\n    - glob: "src/**/*.py"\n      regex: "import db"\n      label: "direct db import"\npolicy:\n  on_fail: block\ndocs:\n  summary: "No direct db imports"\n',
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 0


def test_pattern_gate_negate_missing_pattern_fails(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("# no license header\n", encoding="utf-8")

    (repo / "gates" / "GATE-PAT.yaml").write_text(
        'id: GATE-PAT\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: pattern\n  patterns:\n    - glob: "src/**/*.py"\n      regex: "# Copyright"\n      negate: true\n      label: "license header"\npolicy:\n  on_fail: block\ndocs:\n  summary: "All source files must have copyright"\n',
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 1


def test_pattern_gate_negate_present_passes(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("# Copyright 2026\nimport os\n", encoding="utf-8")

    (repo / "gates" / "GATE-PAT.yaml").write_text(
        'id: GATE-PAT\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: pattern\n  patterns:\n    - glob: "src/**/*.py"\n      regex: "# Copyright"\n      negate: true\n      label: "license header"\npolicy:\n  on_fail: block\ndocs:\n  summary: "All source files must have copyright"\n',
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 0


def test_pattern_gate_invalid_regex(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("hello\n", encoding="utf-8")

    (repo / "gates" / "GATE-PAT.yaml").write_text(
        'id: GATE-PAT\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: pattern\n  patterns:\n    - glob: "src/**/*.py"\n      regex: "[invalid"\npolicy:\n  on_fail: block\ndocs:\n  summary: "Bad regex"\n',
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 1  # invalid regex is a gate failure


def test_pattern_gate_warn_policy(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("import db\n", encoding="utf-8")

    (repo / "gates" / "GATE-PAT.yaml").write_text(
        'id: GATE-PAT\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: pattern\n  patterns:\n    - glob: "src/**/*.py"\n      regex: "import db"\npolicy:\n  on_fail: warn\ndocs:\n  summary: "No direct db imports"\n',
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 0  # warn -> does not fail


# ---------------------------------------------------------------------------
# Threshold gates
# ---------------------------------------------------------------------------

def test_threshold_gate_passes_when_above(tmp_path):
    repo = _setup_repo(tmp_path)
    # Create source files covered by the component
    (repo / "src").mkdir()
    (repo / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")

    (repo / "gates" / "GATE-THR.yaml").write_text(
        'id: GATE-THR\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: threshold\n  metric: intent_coverage\n  threshold: 50\npolicy:\n  on_fail: block\ndocs:\n  summary: "Coverage must be above 50%"\n',
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 0


def test_threshold_gate_fails_when_below(tmp_path):
    repo = _setup_repo(tmp_path)
    # Create source files NOT covered by the component (paths: src/**)
    (repo / "lib").mkdir()
    (repo / "lib" / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (repo / "lib" / "util.py").write_text("print('util')\n", encoding="utf-8")
    (repo / "lib" / "other.py").write_text("print('other')\n", encoding="utf-8")

    (repo / "gates" / "GATE-THR.yaml").write_text(
        'id: GATE-THR\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: threshold\n  metric: intent_coverage\n  threshold: 80\npolicy:\n  on_fail: block\ndocs:\n  summary: "Coverage must be above 80%"\n',
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 1


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def test_json_output(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "gates" / "GATE-0001.yaml").write_text(
        "id: GATE-0001\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: lint-rule\n  checks:\n    - all_specs_have_acceptance_criteria\npolicy:\n  on_fail: block\ndocs:\n  summary: Test gate\n",
        encoding="utf-8",
    )

    args = make_args(repo=str(repo), json=True)
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        rc = cli.cmd_check(args)

    output = f.getvalue()
    data = json.loads(output)
    assert "gates" in data
    assert data["passed"] == 1
    assert data["failed"] == 0
    assert rc == 0


# ---------------------------------------------------------------------------
# Gate results in graph.json
# ---------------------------------------------------------------------------

def test_graph_json_includes_gate_results(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "gates" / "GATE-0001.yaml").write_text(
        "id: GATE-0001\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: lint-rule\n  checks:\n    - all_specs_have_acceptance_criteria\npolicy:\n  on_fail: block\ndocs:\n  summary: Test gate\n",
        encoding="utf-8",
    )

    g = cli.build_graph(repo)
    cli.write_graph_artifacts(repo, g)

    graph_path = repo / ".intent" / "index" / "graph.json"
    assert graph_path.exists()
    data = json.loads(graph_path.read_text())
    assert "gates" in data
    assert len(data["gates"]) == 1
    assert data["gates"][0]["id"] == "GATE-0001"
    assert data["gates"][0]["passed"] is True


# ---------------------------------------------------------------------------
# _run_gate_checks directly
# ---------------------------------------------------------------------------

def test_run_gate_checks_returns_list(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "gates" / "GATE-0001.yaml").write_text(
        "id: GATE-0001\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: lint-rule\n  checks:\n    - all_specs_have_status\npolicy:\n  on_fail: block\n",
        encoding="utf-8",
    )

    g = cli.build_graph(repo)
    results = cli._run_gate_checks(repo, g)
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["passed"] is True
    assert results[0]["kind"] == "lint-rule"


def test_no_gates_dir_returns_empty(tmp_path):
    # Repo without gates dir
    (tmp_path / "components").mkdir()
    (tmp_path / ".intent").mkdir()

    g = cli.build_graph(tmp_path)
    results = cli._run_gate_checks(tmp_path, g)
    assert results == []


def test_multiple_gates_mixed_results(tmp_path):
    repo = _setup_repo(tmp_path)
    # Gate 1: passes
    (repo / "gates" / "GATE-0001.yaml").write_text(
        "id: GATE-0001\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: lint-rule\n  checks:\n    - all_specs_have_status\npolicy:\n  on_fail: block\n",
        encoding="utf-8",
    )
    # Gate 2: fails (command gate)
    (repo / "gates" / "GATE-0002.yaml").write_text(
        'id: GATE-0002\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: command\n  command: ["false"]\npolicy:\n  on_fail: block\n',
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 1  # one gate failed


def test_gates_json_written_to_index(tmp_path):
    repo = _setup_repo(tmp_path)
    (repo / "gates" / "GATE-0001.yaml").write_text(
        "id: GATE-0001\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: lint-rule\n  checks:\n    - all_specs_have_status\npolicy:\n  on_fail: block\n",
        encoding="utf-8",
    )

    args = make_args(repo=str(repo))
    cli.cmd_check(args)

    gates_json = repo / ".intent" / "index" / "gates.json"
    assert gates_json.exists()
    data = json.loads(gates_json.read_text())
    assert len(data) == 1
    assert data[0]["id"] == "GATE-0001"
