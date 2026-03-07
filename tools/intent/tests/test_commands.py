"""Tests for fmt, bootstrap, lint, and gate edge commands."""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": "."}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# fmt
# ---------------------------------------------------------------------------

def test_fmt_inserts_links_section(tmp_path):
    (tmp_path / "intent" / "comp" / "specs").mkdir(parents=True)
    spec = tmp_path / "intent" / "comp" / "specs" / "SPEC-0001-foo.md"
    spec.write_text("---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Foo\n\n## Intent\nTest.\n", encoding="utf-8")

    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_fmt(args)
    assert rc == 0

    content = spec.read_text()
    assert "## Links" in content


def test_fmt_does_not_duplicate_links_section(tmp_path):
    (tmp_path / "intent" / "comp" / "specs").mkdir(parents=True)
    spec = tmp_path / "intent" / "comp" / "specs" / "SPEC-0001-foo.md"
    spec.write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Foo\n\n## Links\n\n- Belongs to: [[COMP-x]]\n",
        encoding="utf-8",
    )
    original = spec.read_text()

    args = make_args(repo=str(tmp_path))
    cli.cmd_fmt(args)

    content = spec.read_text()
    assert content.count("## Links") == 1


def test_fmt_inserts_id_from_filename(tmp_path):
    (tmp_path / "intent" / "comp" / "specs").mkdir(parents=True)
    spec = tmp_path / "intent" / "comp" / "specs" / "SPEC-0042-thing.md"
    spec.write_text("# Thing\n\n## Intent\nTest.\n", encoding="utf-8")

    args = make_args(repo=str(tmp_path))
    cli.cmd_fmt(args)

    content = spec.read_text()
    assert "id: SPEC-0042" in content


def test_fmt_no_intent_dir(tmp_path):
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_fmt(args)
    assert rc == 0


# ---------------------------------------------------------------------------
# bootstrap
# ---------------------------------------------------------------------------

def test_bootstrap_detects_package_json(tmp_path):
    (tmp_path / "my-service").mkdir()
    (tmp_path / "my-service" / "package.json").write_text('{"name":"my-service"}', encoding="utf-8")
    (tmp_path / "components").mkdir()

    args = make_args(repo=str(tmp_path), dry_run=False)
    rc = cli.cmd_bootstrap(args)
    assert rc == 0

    created = tmp_path / "components" / "my-service.yaml"
    assert created.exists()
    content = created.read_text()
    assert "COMP-my-service" in content
    assert "lang: js" in content


def test_bootstrap_dry_run_no_files(tmp_path):
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "go.mod").write_text("module example.com/api\n", encoding="utf-8")
    (tmp_path / "components").mkdir()

    args = make_args(repo=str(tmp_path), dry_run=True)
    cli.cmd_bootstrap(args)

    assert not (tmp_path / "components" / "api.yaml").exists()


def test_bootstrap_skips_existing(tmp_path):
    (tmp_path / "svc").mkdir()
    (tmp_path / "svc" / "pyproject.toml").write_text("[project]\nname='svc'\n", encoding="utf-8")
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "svc.yaml").write_text("id: COMP-svc\nname: Svc\n", encoding="utf-8")

    args = make_args(repo=str(tmp_path), dry_run=False)
    cli.cmd_bootstrap(args)

    # Should not overwrite
    content = (tmp_path / "components" / "svc.yaml").read_text()
    assert "bootstrapped" not in content


def test_bootstrap_no_manifests(tmp_path):
    (tmp_path / "docs").mkdir()
    args = make_args(repo=str(tmp_path), dry_run=False)
    rc = cli.cmd_bootstrap(args)
    assert rc == 0


# ---------------------------------------------------------------------------
# lint with severity
# ---------------------------------------------------------------------------

def test_lint_error_on_missing_id(tmp_path, capsys):
    (tmp_path / "intent" / "comp" / "specs").mkdir(parents=True)
    spec = tmp_path / "intent" / "comp" / "specs" / "SPEC-0001-test.md"
    spec.write_text(
        "---\nstatus: accepted\n---\n\n# Test\n\n## Intent\n.\n## Goals\n.\n## Non-goals\n.\n## Design\n.\n## Acceptance Criteria\n.\n## Links\n.",
        encoding="utf-8",
    )

    args = make_args(repo=str(tmp_path), min_severity="error")
    rc = cli.cmd_lint(args)

    captured = capsys.readouterr()
    assert "ERROR" in captured.out
    assert rc == 1  # errors present


def test_lint_warns_on_missing_status(tmp_path, capsys):
    (tmp_path / "intent" / "comp" / "specs").mkdir(parents=True)
    spec = tmp_path / "intent" / "comp" / "specs" / "SPEC-0001-test.md"
    spec.write_text(
        "---\nid: SPEC-0001\n---\n\n# Test\n\n## Intent\n.\n## Goals\n.\n## Non-goals\n.\n## Design\n.\n## Acceptance Criteria\n.\n## Links\n- Belongs to: [[COMP-comp]]\n",
        encoding="utf-8",
    )
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "comp.yaml").write_text("id: COMP-comp\nname: Comp\n", encoding="utf-8")

    args = make_args(repo=str(tmp_path), min_severity="warn")
    cli.cmd_lint(args)

    captured = capsys.readouterr()
    assert "status" in captured.out.lower()


# ---------------------------------------------------------------------------
# gate edges
# ---------------------------------------------------------------------------

def test_gate_edges_from_applies_to(tmp_path):
    (tmp_path / "gates").mkdir()
    gate_yaml = tmp_path / "gates" / "spec-quality.yaml"
    gate_yaml.write_text(
        "id: GATE-spec-quality\napplies_to:\n  - node: SPEC-0001\n  - node: SPEC-0002\ndocs:\n  summary: Quality gate\n",
        encoding="utf-8",
    )
    edges = cli.discover_gate_edges(tmp_path)
    srcs = {e.src for e in edges}
    assert "SPEC-0001" in srcs
    assert "SPEC-0002" in srcs
    assert all(e.type == "gated_by" for e in edges)
    assert all(e.dst == "GATE-spec-quality" for e in edges)


def test_gate_edges_integrated_in_build_graph(tmp_path):
    (tmp_path / "gates").mkdir()
    (tmp_path / "intent" / "comp" / "specs").mkdir(parents=True)
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "comp.yaml").write_text("id: COMP-comp\nname: Comp\n", encoding="utf-8")
    spec = tmp_path / "intent" / "comp" / "specs" / "SPEC-0001-test.md"
    spec.write_text("---\nid: SPEC-0001\n---\n\n# Test\n", encoding="utf-8")
    gate = tmp_path / "gates" / "q.yaml"
    gate.write_text(
        "id: GATE-q\napplies_to:\n  - node: SPEC-0001\ndocs:\n  summary: Q\n",
        encoding="utf-8",
    )

    g = cli.build_graph(tmp_path)
    gated = [e for e in g.edges if e.type == "gated_by" and e.src == "SPEC-0001"]
    assert len(gated) == 1
    assert gated[0].dst == "GATE-q"
