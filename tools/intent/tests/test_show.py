"""Tests for the sigil show command."""
import argparse
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": ".", "node": "SPEC-0001", "json": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _scaffold(tmp_path):
    """Create a minimal repo with a component, spec, and ADR."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "auth.yaml").write_text(
        "id: COMP-auth\nname: Auth Service\nowners:\n  - team-core\npaths:\n  - src/auth/\n",
        encoding="utf-8",
    )
    (tmp_path / "intent" / "auth" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "auth" / "specs" / "SPEC-0001-jwt.md").write_text(
        "---\nid: SPEC-0001\ntitle: JWT Auth\nstatus: accepted\n---\n\n# JWT Auth\n\n"
        "Authenticate users with JSON Web Tokens.\n\n## Context\n\nWe need auth.\n\n## Links\n\n- [[ADR-0001]]\n",
        encoding="utf-8",
    )
    (tmp_path / "intent" / "auth" / "adrs").mkdir(parents=True)
    (tmp_path / "intent" / "auth" / "adrs" / "ADR-0001-jwt.md").write_text(
        "---\nid: ADR-0001\ntitle: Use JWT\nstatus: accepted\n---\n\n# Use JWT\n\n## Context\n\nNeed stateless auth.\n\n## Decision\n\nUse JWT.\n\n## Consequences\n\nStateless sessions.\n\n## Links\n",
        encoding="utf-8",
    )


def test_show_spec(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), node="SPEC-0001")
    rc = cli.cmd_show(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "SPEC-0001" in out
    assert "JWT Auth" in out
    assert "accepted" in out
    assert "Relationships" in out


def test_show_component(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), node="COMP-auth")
    rc = cli.cmd_show(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "COMP-auth" in out
    assert "Auth Service" in out
    assert "component" in out


def test_show_fuzzy_match(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), node="spec-0001")
    rc = cli.cmd_show(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "SPEC-0001" in out


def test_show_not_found(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), node="SPEC-9999")
    rc = cli.cmd_show(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "No node found" in out or "No exact match" in out


def test_show_ambiguous(tmp_path, capsys):
    _scaffold(tmp_path)
    # "0001" matches both SPEC-0001 and ADR-0001 — ambiguous
    args = make_args(repo=str(tmp_path), node="0001")
    rc = cli.cmd_show(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "Ambiguous" in out or "Did you mean" in out


def test_show_json(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), node="SPEC-0001", json=True)
    rc = cli.cmd_show(args)
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["id"] == "SPEC-0001"
    assert data["type"] == "spec"
    assert data["status"] == "accepted"
    assert "outgoing" in data
    assert "incoming" in data


def test_show_content_snippet(tmp_path, capsys):
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), node="SPEC-0001")
    rc = cli.cmd_show(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Content" in out
    assert "JSON Web Tokens" in out


def test_show_empty_repo(tmp_path, capsys):
    args = make_args(repo=str(tmp_path), node="anything")
    rc = cli.cmd_show(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "No node found" in out or "No exact match" in out


def test_show_not_found_json(tmp_path, capsys):
    """show --json should return structured error when node not found."""
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), node="nonexistent", json=True)
    rc = cli.cmd_show(args)
    assert rc == 1
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["error"] == "not_found"
    assert data["query"] == "nonexistent"
    assert isinstance(data["suggestions"], list)


def test_show_not_found_json_with_suggestions(tmp_path, capsys):
    """show --json should include suggestions for partial matches."""
    _scaffold(tmp_path)
    args = make_args(repo=str(tmp_path), node="jwt-auth-stuff", json=True)
    rc = cli.cmd_show(args)
    assert rc == 1
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["error"] == "not_found"
    assert len(data["suggestions"]) > 0
