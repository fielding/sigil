"""Tests for _compute_coverage, cmd_coverage, and coverage integration."""
import sys
import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": "."}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _setup_full_repo(tmp_path):
    """Create a repo with components, specs (with/without AC), and ADRs."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    (tmp_path / "components" / "web.yaml").write_text("id: COMP-web\nname: Web\n")
    (tmp_path / "components" / "orphan.yaml").write_text("id: COMP-orphan\nname: Orphan\n")

    # Spec with acceptance criteria, belonging to api
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-api.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# API Spec\n\n## Acceptance Criteria\n\n- Works\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )

    # Spec without acceptance criteria, belonging to web
    (tmp_path / "intent" / "web" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "web" / "specs" / "SPEC-0002-web.md").write_text(
        "---\nid: SPEC-0002\nstatus: draft\n---\n\n# Web Spec\n\nNo AC here.\n\n## Links\n\n- Belongs to: [[COMP-web]]\n"
    )

    # ADR accepted
    (tmp_path / "intent" / "api" / "adrs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "adrs" / "ADR-0001-rest.md").write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# REST\n\n## Links\n\n- Decided by: [[SPEC-0001]]\n"
    )

    # ADR draft
    (tmp_path / "intent" / "web" / "adrs").mkdir(parents=True)
    (tmp_path / "intent" / "web" / "adrs" / "ADR-0002-react.md").write_text(
        "---\nid: ADR-0002\nstatus: draft\n---\n\n# React\n\n## Links\n\n- Decided by: [[SPEC-0002]]\n"
    )

    (tmp_path / "gates").mkdir()
    (tmp_path / ".intent" / "index").mkdir(parents=True)


def _setup_empty_repo(tmp_path):
    (tmp_path / ".intent").mkdir()


# ---------------------------------------------------------------------------
# _compute_coverage
# ---------------------------------------------------------------------------

def test_compute_coverage_full_repo(tmp_path):
    """Coverage should compute correct metrics for a mixed repo."""
    _setup_full_repo(tmp_path)
    g = cli.build_graph(tmp_path)
    cov = cli._compute_coverage(tmp_path, g)

    assert 0 <= cov["score"] <= 100
    assert cov["stats"]["components"] == 3
    assert cov["stats"]["specs"] == 2
    assert cov["stats"]["adrs"] == 2

    m = cov["metrics"]
    # 2 of 3 components have specs (api, web have specs; orphan does not)
    assert m["components_with_spec"]["value"] == 2
    assert m["components_with_spec"]["total"] == 3
    # 1 of 2 specs has acceptance criteria
    assert m["specs_with_acceptance"]["value"] == 1
    assert m["specs_with_acceptance"]["total"] == 2
    # Both ADRs have a status field
    assert m["adrs_with_status"]["value"] == 2
    # 1 ADR is accepted
    assert m["adrs_accepted"]["value"] == 1
    assert m["adrs_accepted"]["total"] == 2


def test_compute_coverage_empty_repo(tmp_path):
    """Coverage on empty repo should return 0 score."""
    _setup_empty_repo(tmp_path)
    g = cli.build_graph(tmp_path)
    cov = cli._compute_coverage(tmp_path, g)
    assert cov["score"] == 0
    assert cov["stats"]["components"] == 0
    assert cov["components"] == []
    assert cov["findings"] == []


def test_compute_coverage_components_detail(tmp_path):
    """Per-component details should reflect coverage status."""
    _setup_full_repo(tmp_path)
    g = cli.build_graph(tmp_path)
    cov = cli._compute_coverage(tmp_path, g)

    by_id = {c["id"]: c for c in cov["components"]}
    # api has spec + ADR = green
    assert by_id["COMP-api"]["has_spec"] is True
    assert by_id["COMP-api"]["adr_count"] >= 1
    assert by_id["COMP-api"]["level"] == "green"
    # web has spec but no ADR linked via decided_by to its spec (ADR-0002 links to SPEC-0002)
    assert by_id["COMP-web"]["has_spec"] is True
    # orphan has neither spec nor ADR = red
    assert by_id["COMP-orphan"]["has_spec"] is False
    assert by_id["COMP-orphan"]["level"] == "red"


def test_compute_coverage_findings(tmp_path):
    """Findings should flag components without specs and draft ADRs."""
    _setup_full_repo(tmp_path)
    g = cli.build_graph(tmp_path)
    cov = cli._compute_coverage(tmp_path, g)

    msgs = [f["message"] for f in cov["findings"]]
    # Should flag orphan component
    assert any("component" in m.lower() and "no governing spec" in m for m in msgs)
    # Should flag draft ADR
    assert any("draft" in m.lower() for m in msgs)


def test_coverage_color_thresholds():
    """Color helper should return correct colors for score ranges."""
    assert cli._coverage_color(90) == "#04b372"
    assert cli._coverage_color(70) == "#458ae2"
    assert cli._coverage_color(50) == "#f2a633"
    assert cli._coverage_color(20) == "#e7349c"


def test_coverage_label_thresholds():
    """Label helper should return correct labels for score ranges."""
    assert cli._coverage_label(85) == "excellent"
    assert cli._coverage_label(65) == "good"
    assert cli._coverage_label(45) == "fair"
    assert cli._coverage_label(25) == "needs work"


# ---------------------------------------------------------------------------
# cmd_coverage
# ---------------------------------------------------------------------------

def test_cmd_coverage_text_output(tmp_path, capsys):
    """cmd_coverage should print a formatted report."""
    _setup_full_repo(tmp_path)
    args = make_args(repo=str(tmp_path), json=False)
    rc = cli.cmd_coverage(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Intent Coverage:" in out
    assert "Components with spec:" in out
    assert "Specs with acceptance:" in out
    assert "ADRs accepted:" in out
    assert "Components:" in out
    assert "Findings:" in out


def test_cmd_coverage_json_output(tmp_path, capsys):
    """cmd_coverage --json should output valid JSON."""
    _setup_full_repo(tmp_path)
    args = make_args(repo=str(tmp_path), json=True)
    rc = cli.cmd_coverage(args)
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "score" in data
    assert "metrics" in data
    assert "components" in data
    assert "findings" in data


def test_cmd_coverage_writes_json(tmp_path):
    """cmd_coverage should write coverage.json to .intent/index/."""
    _setup_full_repo(tmp_path)
    args = make_args(repo=str(tmp_path), json=False)
    cli.cmd_coverage(args)
    cov_path = tmp_path / ".intent" / "index" / "coverage.json"
    assert cov_path.exists()
    data = json.loads(cov_path.read_text())
    assert data["score"] >= 0


def test_cmd_coverage_empty_repo(tmp_path, capsys):
    """cmd_coverage on empty repo should succeed."""
    _setup_empty_repo(tmp_path)
    args = make_args(repo=str(tmp_path), json=False)
    rc = cli.cmd_coverage(args)
    assert rc == 0


# ---------------------------------------------------------------------------
# Integration: index writes coverage.json
# ---------------------------------------------------------------------------

def test_index_writes_coverage_json(tmp_path):
    """sigil index should also produce coverage.json."""
    _setup_full_repo(tmp_path)
    g = cli.build_graph(tmp_path)
    cli.write_graph_artifacts(tmp_path, g)
    cov_path = tmp_path / ".intent" / "index" / "coverage.json"
    assert cov_path.exists()
    data = json.loads(cov_path.read_text())
    assert "score" in data
    assert "metrics" in data
    assert "components" in data


# ---------------------------------------------------------------------------
# badge reuses _compute_coverage
# ---------------------------------------------------------------------------

def test_badge_uses_compute_coverage(tmp_path):
    """cmd_badge should produce consistent score with cmd_coverage."""
    _setup_full_repo(tmp_path)
    g = cli.build_graph(tmp_path)
    cov = cli._compute_coverage(tmp_path, g)
    badge_path = tmp_path / "badge.svg"
    args = make_args(repo=str(tmp_path), output=str(badge_path))
    cli.cmd_badge(args)
    svg = badge_path.read_text()
    assert f"{cov['score']}%" in svg
