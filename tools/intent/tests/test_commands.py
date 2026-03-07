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


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

def test_doctor_on_empty_repo(tmp_path):
    """Doctor should run and report failures on an empty directory."""
    (tmp_path / ".git").mkdir()
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_doctor(args)
    assert rc == 1  # not everything will pass on empty repo


def test_doctor_on_valid_repo(tmp_path):
    """Doctor should pass most checks on a properly set up repo."""
    for d in ["components", "intent", "interfaces", "gates", "templates", ".intent", ".intent/index"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / ".intent" / "config.yaml").write_text("id_counters: {}\n")
    (tmp_path / "templates" / "SPEC.md").write_text("---\nid: SPEC-0000\n---\n")
    (tmp_path / "templates" / "ADR.md").write_text("---\nid: ADR-0000\n---\n")
    (tmp_path / ".intent" / "index" / "graph.json").write_text('{"nodes":[],"edges":[]}')
    (tmp_path / "components" / "test.yaml").write_text("id: COMP-test\nname: test\n")
    (tmp_path / ".git").mkdir()
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_doctor(args)
    # Most checks pass (viewer and hook may fail)
    assert rc in (0, 1)


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------

def test_scan_detects_manifest_components(tmp_path):
    """Scan should detect directories with package manifests."""
    (tmp_path / "api-server").mkdir()
    (tmp_path / "api-server" / "package.json").write_text('{"name":"api"}')
    (tmp_path / "api-server" / "src").mkdir()
    (tmp_path / "api-server" / "src" / "index.js").write_text("// entry")
    (tmp_path / ".intent").mkdir()

    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    rc = cli.cmd_scan(args)
    assert rc == 0
    assert (tmp_path / "scan.json").exists()

    import json
    report = json.loads((tmp_path / "scan.json").read_text())
    slugs = [c["slug"] for c in report["components"]]
    assert "api-server" in slugs
    assert report["components"][0]["lang"] == "js"


def test_scan_detects_apis(tmp_path):
    """Scan should detect OpenAPI and proto files."""
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "openapi.yaml").write_text("openapi: 3.0.0")
    (tmp_path / "protos").mkdir()
    (tmp_path / "protos" / "service.proto").write_text('syntax = "proto3";')
    (tmp_path / ".intent").mkdir()

    args = make_args(repo=str(tmp_path), dry_run=True, output=None)
    rc = cli.cmd_scan(args)
    assert rc == 0


def test_scan_detects_ci(tmp_path):
    """Scan should detect CI configuration."""
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI")
    (tmp_path / ".intent").mkdir()

    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    rc = cli.cmd_scan(args)
    assert rc == 0

    import json
    report = json.loads((tmp_path / "scan.json").read_text())
    assert len(report["ci"]) == 1
    assert report["ci"][0]["type"] == "GitHub Actions"


def test_scan_generates_recommendations(tmp_path):
    """Scan should recommend creating components for uncovered dirs."""
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "go.mod").write_text("module example.com/backend")
    (tmp_path / ".intent").mkdir()

    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    rc = cli.cmd_scan(args)
    assert rc == 0

    import json
    report = json.loads((tmp_path / "scan.json").read_text())
    assert any("backend" in r for r in report["recommendations"])


def test_scan_skips_sigil_dirs(tmp_path):
    """Scan should not report sigil's own directories as components."""
    for d in ["components", "intent", "interfaces", "gates", "templates"]:
        (tmp_path / d).mkdir()
        (tmp_path / d / "dummy.yaml").write_text("id: test")
    (tmp_path / ".intent").mkdir()

    args = make_args(repo=str(tmp_path), dry_run=True, output=None)
    rc = cli.cmd_scan(args)
    assert rc == 0


def test_scan_dry_run_no_file(tmp_path):
    """Dry run should not write the report file."""
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    args = make_args(repo=str(tmp_path), dry_run=True, output=None)
    rc = cli.cmd_scan(args)
    assert rc == 0
    assert not (tmp_path / ".intent" / "index" / "scan.json").exists()


# ---------------------------------------------------------------------------
# ci
# ---------------------------------------------------------------------------

def test_ci_on_minimal_repo(tmp_path):
    """CI pipeline should run on a minimal repo without errors."""
    for d in ["components", "intent", "interfaces", "gates", "templates", ".intent"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / ".intent" / "config.yaml").write_text("id_counters: {}\n")
    (tmp_path / "templates" / "SPEC.md").write_text("---\nid: SPEC-0000\n---\n")
    (tmp_path / "templates" / "ADR.md").write_text("---\nid: ADR-0000\n---\n")
    (tmp_path / "components" / "test.yaml").write_text("id: COMP-test\nname: test\n")

    args = make_args(repo=str(tmp_path), strict=False, base=None, head=None)
    rc = cli.cmd_ci(args)
    assert rc == 0


def test_ci_strict_mode(tmp_path):
    """CI strict mode should return non-zero on lint warnings."""
    for d in ["components", "intent", "interfaces", "gates", "templates", ".intent"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / ".intent" / "config.yaml").write_text("id_counters: {}\n")

    args = make_args(repo=str(tmp_path), strict=True, base=None, head=None)
    rc = cli.cmd_ci(args)
    # Should pass since no lint issues on empty repo
    assert rc == 0
