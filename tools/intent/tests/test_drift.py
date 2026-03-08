"""Tests for cmd_drift and cmd_suggest."""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": "."}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _setup_drift_repo(tmp_path):
    """Create a repo with component path patterns and source files."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text(
        'id: COMP-api\nname: API\npaths:\n  - "api/**"\n'
    )
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-endpoints.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Endpoints\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    # Create some source files
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "server.py").write_text("# server")
    # Create unowned file
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "deploy.sh").write_text("#!/bin/bash")
    # .intent dir
    (tmp_path / ".intent" / "index").mkdir(parents=True)


def test_drift_detects_unowned_files(tmp_path, capsys):
    """Drift should detect files not mapped to any component."""
    _setup_drift_repo(tmp_path)
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_drift(args)
    assert rc == 1  # drift detected
    out = capsys.readouterr().out
    assert "Drift Detection Report" in out
    assert "Unowned files:" in out or "file(s) not mapped" in out


def test_drift_no_drift(tmp_path, capsys):
    """Drift should report clean when all files are mapped."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text(
        'id: COMP-api\nname: API\npaths:\n  - "api/**"\n'
    )
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-endpoints.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Endpoints\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "server.py").write_text("# server")
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_drift(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No drift detected" in out


def test_drift_writes_json(tmp_path):
    """Drift should write drift.json to index dir."""
    _setup_drift_repo(tmp_path)
    args = make_args(repo=str(tmp_path))
    cli.cmd_drift(args)
    drift_json = tmp_path / ".intent" / "index" / "drift.json"
    assert drift_json.exists()
    import json
    data = json.loads(drift_json.read_text())
    assert "scanned" in data
    assert "findings" in data


def test_drift_no_spec_warning(tmp_path, capsys):
    """Drift should warn about components with code but no spec."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text(
        'id: COMP-api\nname: API\npaths:\n  - "api/**"\n'
    )
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "server.py").write_text("# server")
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_drift(args)
    out = capsys.readouterr().out
    assert "no governing spec" in out


def test_drift_spec_no_code(tmp_path, capsys):
    """Drift should report components with specs but no code files."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text(
        'id: COMP-api\nname: API\npaths:\n  - "api/**"\n'
    )
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Test\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    # No api/ directory at all
    args = make_args(repo=str(tmp_path))
    cli.cmd_drift(args)
    out = capsys.readouterr().out
    assert "specs but no matching code" in out


def test_drift_json_output(tmp_path, capsys):
    """Drift --json should print valid JSON to stdout."""
    _setup_drift_repo(tmp_path)
    import json
    args = make_args(repo=str(tmp_path), json=True)
    rc = cli.cmd_drift(args)
    assert rc == 1  # drift detected
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "scanned" in data
    assert "drift_signals" in data
    assert data["drift_signals"] > 0
    assert isinstance(data["findings"], list)
    # Should NOT contain terminal formatting
    assert "Drift Detection Report" not in out


def test_drift_many_unowned_truncates(tmp_path, capsys):
    """Drift should truncate unowned file list at 15."""
    (tmp_path / "components").mkdir()
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    (tmp_path / "src").mkdir()
    for i in range(20):
        (tmp_path / "src" / f"file{i}.py").write_text(f"# file {i}")
    args = make_args(repo=str(tmp_path))
    cli.cmd_drift(args)
    out = capsys.readouterr().out
    assert "more" in out


# ---------------------------------------------------------------------------
# cmd_suggest
# ---------------------------------------------------------------------------

def test_suggest_governed_file(tmp_path, capsys):
    """Suggest should show specs, ADRs, and gates for a governed file."""
    _setup_drift_repo(tmp_path)
    # Add a gate
    (tmp_path / "gates").mkdir()
    (tmp_path / "gates" / "GATE-0001-quality.yaml").write_text(
        "id: GATE-0001\napplies_to:\n  - node: COMP-api\ndocs:\n  summary: Quality gate\nchecks: []\n"
    )
    args = make_args(repo=str(tmp_path), path="api/server.py")
    rc = cli.cmd_suggest(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "COMP-api" in out
    assert "SPEC-0001" in out
    assert "Governing Specs" in out


def test_suggest_ungoverned_file(tmp_path, capsys):
    """Suggest should report when no component owns the file."""
    (tmp_path / "components").mkdir()
    (tmp_path / "random.txt").write_text("hello")
    args = make_args(repo=str(tmp_path), path="random.txt")
    rc = cli.cmd_suggest(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No component owns this file" in out


def test_suggest_with_adrs(tmp_path, capsys):
    """Suggest should show related ADRs."""
    _setup_drift_repo(tmp_path)
    (tmp_path / "intent" / "api" / "adrs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "intent" / "api" / "adrs" / "ADR-0001-rest.md").write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# REST\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    args = make_args(repo=str(tmp_path), path="api/server.py")
    rc = cli.cmd_suggest(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "ADR-0001" in out
    assert "Relevant ADRs" in out


def test_suggest_with_interface(tmp_path, capsys):
    """Suggest should show related interfaces."""
    _setup_drift_repo(tmp_path)
    (tmp_path / "interfaces" / "REST-API-V1").mkdir(parents=True)
    (tmp_path / "interfaces" / "REST-API-V1" / "README.md").write_text(
        "# REST API V1\n\nProvided by [[COMP-api]].\n"
    )
    args = make_args(repo=str(tmp_path), path="api/server.py")
    rc = cli.cmd_suggest(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "COMP-api" in out
