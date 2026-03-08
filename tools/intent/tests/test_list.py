"""Tests for the sigil list command."""
import argparse
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": ".", "type": None, "sort": "id", "json": False}
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


def test_list_sort_by_type(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), sort="type")
    rc = cli.cmd_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "4 node(s)" in out
