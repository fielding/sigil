"""Tests for the sigil list command."""
import argparse
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": ".", "type": None, "status": None, "component": None, "sort": "id", "json": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _scaffold(tmp_path):
    """Create a minimal repo with components, specs, and an ADR."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "auth.yaml").write_text(
        "id: COMP-auth\nname: Auth Service\nowners:\n  - team-core\npaths:\n  - src/auth/\n",
        encoding="utf-8",
    )
    (tmp_path / "components" / "web.yaml").write_text(
        "id: COMP-web\nname: Web App\nowners:\n  - team-frontend\npaths:\n  - src/web/\n",
        encoding="utf-8",
    )
    (tmp_path / "intent" / "auth" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "auth" / "specs" / "SPEC-0001-jwt.md").write_text(
        "---\nid: SPEC-0001\ntitle: JWT Auth\nstatus: accepted\n---\n\n# JWT Auth\n",
        encoding="utf-8",
    )
    (tmp_path / "intent" / "auth" / "adrs").mkdir(parents=True)
    (tmp_path / "intent" / "auth" / "adrs" / "ADR-0001-jwt.md").write_text(
        "---\nid: ADR-0001\ntitle: Use JWT\nstatus: accepted\n---\n\n# Use JWT\n",
        encoding="utf-8",
    )


def test_list_all(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "4 node(s)" in out
    assert "COMP-auth" in out
    assert "COMP-web" in out
    assert "SPEC-0001" in out
    assert "ADR-0001" in out


def test_list_filter_components(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), type="components")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "2 node(s) (components)" in out
    assert "COMP-auth" in out
    assert "COMP-web" in out
    assert "SPEC-0001" not in out


def test_list_filter_specs(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), type="specs")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "1 node(s) (specs)" in out
    assert "SPEC-0001" in out


def test_list_invalid_type(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), type="widgets")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No nodes of type" in out
    assert "Available types" in out


def test_list_json(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), json=True)
    rc = cli.cmd_list(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["count"] == 4
    assert len(data["nodes"]) == 4
    ids = {n["id"] for n in data["nodes"]}
    assert "COMP-auth" in ids
    assert "SPEC-0001" in ids


def test_list_json_filtered(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), type="adrs", json=True)
    rc = cli.cmd_list(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["count"] == 1
    assert data["nodes"][0]["id"] == "ADR-0001"


def test_list_empty(tmp_path, capsys):
    (tmp_path / "components").mkdir()
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No intent nodes" in out


def test_list_shows_status(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "[accepted]" in out
    # Components should not show status
    for line in out.splitlines():
        if "COMP-" in line:
            assert "[" not in line


def test_list_status_in_json(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), json=True)
    rc = cli.cmd_list(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    spec = next(n for n in data["nodes"] if n["id"] == "SPEC-0001")
    assert spec["status"] == "accepted"
    adr = next(n for n in data["nodes"] if n["id"] == "ADR-0001")
    assert adr["status"] == "accepted"
    # Components should not have status
    comp = next(n for n in data["nodes"] if n["id"] == "COMP-auth")
    assert "status" not in comp


def test_list_filtered_shows_status(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), type="specs")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "SPEC-0001" in out
    assert "[accepted]" in out


def test_list_sort_by_type(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), sort="type")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "4 node(s)" in out


def _scaffold_multi(tmp_path):
    """Create a repo with multiple components/specs at different statuses."""
    _scaffold(tmp_path)  # auth: SPEC-0001 accepted, ADR-0001 accepted; web: nothing
    # Add a proposed spec under web
    (tmp_path / "intent" / "web" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "web" / "specs" / "SPEC-0002-ui.md").write_text(
        "---\nid: SPEC-0002\ntitle: Web UI\nstatus: proposed\n---\n\n# Web UI\n",
        encoding="utf-8",
    )
    # Add a draft ADR under web
    (tmp_path / "intent" / "web" / "adrs").mkdir(parents=True)
    (tmp_path / "intent" / "web" / "adrs" / "ADR-0002-react.md").write_text(
        "---\nid: ADR-0002\ntitle: Use React\nstatus: draft\n---\n\n# Use React\n",
        encoding="utf-8",
    )


def test_list_filter_by_status(tmp_path, capsys):
    _scaffold_multi(tmp_path)
    args = make_args(repo=str(tmp_path), status="proposed")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "SPEC-0002" in out
    assert "SPEC-0001" not in out  # accepted, not proposed


def test_list_filter_by_status_accepted(tmp_path, capsys):
    _scaffold_multi(tmp_path)
    args = make_args(repo=str(tmp_path), status="accepted")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "SPEC-0001" in out
    assert "ADR-0001" in out
    assert "SPEC-0002" not in out


def test_list_filter_by_status_json(tmp_path, capsys):
    _scaffold_multi(tmp_path)
    args = make_args(repo=str(tmp_path), status="draft", json=True)
    rc = cli.cmd_list(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["count"] == 1
    assert data["nodes"][0]["id"] == "ADR-0002"


def test_list_filter_by_status_no_match(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), status="deprecated")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No nodes matching" in out
    assert "status=deprecated" in out


def test_list_filter_by_component(tmp_path, capsys):
    _scaffold_multi(tmp_path)
    args = make_args(repo=str(tmp_path), component="auth")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "COMP-auth" in out
    assert "SPEC-0001" in out
    assert "ADR-0001" in out
    assert "SPEC-0002" not in out  # belongs to web
    assert "COMP-web" not in out


def test_list_filter_by_component_json(tmp_path, capsys):
    _scaffold_multi(tmp_path)
    args = make_args(repo=str(tmp_path), component="web", json=True)
    rc = cli.cmd_list(args)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    ids = {n["id"] for n in data["nodes"]}
    assert "COMP-web" in ids
    assert "SPEC-0002" in ids
    assert "ADR-0002" in ids
    assert "COMP-auth" not in ids


def test_list_filter_by_component_no_match(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), component="nonexistent")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No nodes matching" in out
    assert "component=nonexistent" in out


def test_list_combined_status_and_component(tmp_path, capsys):
    _scaffold_multi(tmp_path)
    args = make_args(repo=str(tmp_path), type="specs", status="proposed", component="web")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "SPEC-0002" in out
    assert "1 node(s)" in out


def test_list_combined_filters_no_match(tmp_path, capsys):
    _scaffold_multi(tmp_path)
    args = make_args(repo=str(tmp_path), status="proposed", component="auth")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No nodes matching" in out
