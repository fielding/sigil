"""Tests for cmd_status."""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": "."}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _setup_repo(tmp_path):
    """Create a repo with components, specs, ADRs for status tests."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text(
        "id: COMP-api\nname: API\npaths:\n  - \"api/**\"\n"
    )
    (tmp_path / "components" / "web.yaml").write_text(
        "id: COMP-web\nname: Web\n"
    )
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-endpoints.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Endpoints\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / "intent" / "api" / "adrs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "adrs" / "ADR-0001-rest.md").write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# REST\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / "intent" / "api" / "adrs" / "ADR-0002-draft.md").write_text(
        "---\nid: ADR-0002\nstatus: draft\n---\n\n# Draft Decision\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / "gates").mkdir()
    (tmp_path / "gates" / "GATE-0001-quality.yaml").write_text(
        "id: GATE-0001\ndocs:\n  summary: Quality gate\nchecks: []\n"
    )
    (tmp_path / "interfaces").mkdir()


def test_status_with_populated_repo(tmp_path, capsys):
    """Status should show health bar, node counts, edge counts, and issues."""
    _setup_repo(tmp_path)
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_status(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Sigil Intent Status" in out
    assert "Health:" in out
    assert "Nodes:" in out
    assert "Edges:" in out
    assert "component:" in out
    assert "spec:" in out


def test_status_reports_uncomped_components(tmp_path, capsys):
    """Status should flag components with no governing spec."""
    _setup_repo(tmp_path)
    args = make_args(repo=str(tmp_path))
    cli.cmd_status(args)
    out = capsys.readouterr().out
    # COMP-web has no spec
    assert "component(s) have no governing spec" in out


def test_status_reports_draft_adrs(tmp_path, capsys):
    """Status should flag draft ADRs."""
    _setup_repo(tmp_path)
    args = make_args(repo=str(tmp_path))
    cli.cmd_status(args)
    out = capsys.readouterr().out
    assert "ADR(s) still in draft/proposed" in out


def test_status_empty_repo(tmp_path, capsys):
    """Status on an uninitialized repo should show onboarding guidance."""
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_status(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No intent graph found" in out
    assert "sigil init" in out
    assert "sigil doctor" in out


def test_status_initialized_but_empty_repo(tmp_path, capsys):
    """Status on an initialized repo with no nodes should report zero nodes."""
    (tmp_path / ".intent").mkdir()
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_status(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Nodes: 0" in out
    assert "No intent documents yet" in out
    assert "sigil bootstrap" in out


def test_status_dangling_reference(tmp_path, capsys):
    """Status should report dangling references (typed links to non-existent nodes)."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    # Use a typed link (Depends on) to create a real edge to a nonexistent node
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Test\n\n## Links\n\n- Belongs to: [[COMP-api]]\n- Depends on: [[NONEXISTENT-999]]\n"
    )
    args = make_args(repo=str(tmp_path))
    cli.cmd_status(args)
    out = capsys.readouterr().out
    assert "dangling reference" in out


def test_status_perfect_repo(tmp_path, capsys):
    """Status on a repo with all components covered should show no issues."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Test\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    args = make_args(repo=str(tmp_path))
    cli.cmd_status(args)
    out = capsys.readouterr().out
    assert "No issues found" in out
