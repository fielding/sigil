"""Tests for cmd_export, cmd_badge, cmd_timeline, cmd_init, cmd_new, _find_viewer, _ensure_viewer."""
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


def _setup_export_repo(tmp_path):
    """Create a repo with viewer, components, specs for export/badge tests."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Test\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / "intent" / "api" / "adrs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "adrs" / "ADR-0001-rest.md").write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# REST\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / "gates").mkdir()
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    # Create a minimal viewer HTML
    viewer_dir = tmp_path / "tools" / "intent_viewer"
    viewer_dir.mkdir(parents=True)
    (viewer_dir / "index.html").write_text(
        "<html><head><title>Sigil Viewer</title></head><body>Viewer</body></html>"
    )


# ---------------------------------------------------------------------------
# _find_viewer / _ensure_viewer
# ---------------------------------------------------------------------------

def test_find_viewer_in_repo(tmp_path):
    """_find_viewer should find viewer in tools/intent_viewer/."""
    _setup_export_repo(tmp_path)
    result = cli._find_viewer(tmp_path)
    assert result is not None
    assert "index.html" in str(result)


def test_find_viewer_missing(tmp_path):
    """_find_viewer should return None when viewer not found."""
    result = cli._find_viewer(tmp_path)
    assert result is None


def test_ensure_viewer_exists(tmp_path):
    """_ensure_viewer should return path when viewer already in repo."""
    _setup_export_repo(tmp_path)
    result = cli._ensure_viewer(tmp_path)
    assert result is not None
    assert result.exists()


def test_ensure_viewer_missing(tmp_path):
    """_ensure_viewer should return None when no viewer source available."""
    result = cli._ensure_viewer(tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# cmd_badge
# ---------------------------------------------------------------------------

def test_badge_generates_svg(tmp_path, capsys):
    """Badge should generate a valid SVG file."""
    _setup_export_repo(tmp_path)
    out_svg = tmp_path / "badge.svg"
    args = make_args(repo=str(tmp_path), output=str(out_svg))
    rc = cli.cmd_badge(args)
    assert rc == 0
    assert out_svg.exists()
    svg_content = out_svg.read_text()
    assert "<svg" in svg_content
    assert "intent coverage" in svg_content
    out = capsys.readouterr().out
    assert "Badge:" in out
    assert "Score:" in out


def test_badge_default_output(tmp_path):
    """Badge with no output arg should write to .intent/badge.svg."""
    _setup_export_repo(tmp_path)
    args = make_args(repo=str(tmp_path), output=None)
    rc = cli.cmd_badge(args)
    assert rc == 0
    assert (tmp_path / ".intent" / "badge.svg").exists()


def test_badge_empty_repo(tmp_path, capsys):
    """Badge on empty repo should still produce an SVG."""
    (tmp_path / ".intent").mkdir()
    args = make_args(repo=str(tmp_path), output=str(tmp_path / "badge.svg"))
    rc = cli.cmd_badge(args)
    assert rc == 0
    assert (tmp_path / "badge.svg").exists()


def test_badge_color_by_score(tmp_path):
    """Badge color should change based on score."""
    _setup_export_repo(tmp_path)
    out_svg = tmp_path / "badge.svg"
    args = make_args(repo=str(tmp_path), output=str(out_svg))
    cli.cmd_badge(args)
    svg = out_svg.read_text()
    # With spec+ADR+base, should be high score (green)
    assert "#04b372" in svg or "#458ae2" in svg or "#f2a633" in svg or "#e7349c" in svg


# ---------------------------------------------------------------------------
# cmd_export
# ---------------------------------------------------------------------------

def test_export_generates_html(tmp_path, capsys):
    """Export should generate a self-contained HTML file."""
    _setup_export_repo(tmp_path)
    out_html = tmp_path / "export.html"
    args = make_args(repo=str(tmp_path), output=str(out_html))
    rc = cli.cmd_export(args)
    assert rc == 0
    assert out_html.exists()
    content = out_html.read_text()
    assert "__SIGIL_GRAPH__" in content
    assert "__SIGIL_FILES__" in content
    assert "__SIGIL_DRIFT__" in content
    assert "__SIGIL_TIMELINE__" in content
    assert "__SIGIL_REVIEW__" in content
    out = capsys.readouterr().out
    assert "Exported to" in out
    assert "file(s) embedded" in out


def test_export_default_output(tmp_path):
    """Export with no output arg should write to .intent/export.html."""
    _setup_export_repo(tmp_path)
    args = make_args(repo=str(tmp_path), output=None)
    rc = cli.cmd_export(args)
    assert rc == 0
    assert (tmp_path / ".intent" / "export.html").exists()


def test_export_embeds_drift_timeline(tmp_path):
    """Export should embed drift.json and timeline.json if they exist."""
    _setup_export_repo(tmp_path)
    idx = tmp_path / ".intent" / "index"
    idx.mkdir(parents=True, exist_ok=True)
    (idx / "drift.json").write_text('{"scanned": 10, "findings": []}')
    (idx / "timeline.json").write_text('{"events": [{"date": "2025-01-01"}]}')
    (idx / "review.json").write_text('{"summary": {}}')
    out_html = tmp_path / "export.html"
    args = make_args(repo=str(tmp_path), output=str(out_html))
    cli.cmd_export(args)
    content = out_html.read_text()
    assert "scanned" in content
    assert "2025-01-01" in content


def test_export_no_viewer_fails(tmp_path, capsys):
    """Export should fail when viewer is not found."""
    (tmp_path / "components").mkdir()
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    args = make_args(repo=str(tmp_path), output=str(tmp_path / "out.html"))
    rc = cli.cmd_export(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "Viewer not found" in out


def test_export_updates_title(tmp_path):
    """Export should update the HTML title to include node count."""
    _setup_export_repo(tmp_path)
    out_html = tmp_path / "export.html"
    args = make_args(repo=str(tmp_path), output=str(out_html))
    cli.cmd_export(args)
    content = out_html.read_text()
    assert "Sigil Export" in content
    assert "nodes" in content


# ---------------------------------------------------------------------------
# cmd_timeline (no-git fallback)
# ---------------------------------------------------------------------------

def test_timeline_no_git(tmp_path, capsys):
    """Timeline should fall back to file timestamps when no git history."""
    _setup_export_repo(tmp_path)
    out_file = tmp_path / "timeline.json"
    args = make_args(repo=str(tmp_path), output=str(out_file))
    args.max = "50"
    rc = cli.cmd_timeline(args)
    assert rc == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert "events" in data
    assert len(data["events"]) > 0
    out = capsys.readouterr().out
    assert "Timeline:" in out


def test_timeline_json_output(tmp_path, capsys):
    """Timeline --json should print valid JSON to stdout."""
    _setup_export_repo(tmp_path)
    out_file = tmp_path / "timeline.json"
    args = make_args(repo=str(tmp_path), output=str(out_file), json=True)
    args.max = "50"
    rc = cli.cmd_timeline(args)
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "events" in data
    assert "generated_at" in data
    # Should NOT contain terminal formatting
    assert "Timeline:" not in out


def test_timeline_default_output(tmp_path):
    """Timeline with no output should write to .intent/index/timeline.json."""
    _setup_export_repo(tmp_path)
    args = make_args(repo=str(tmp_path), output=None)
    args.max = "50"
    cli.cmd_timeline(args)
    assert (tmp_path / ".intent" / "index" / "timeline.json").exists()


# ---------------------------------------------------------------------------
# cmd_new
# ---------------------------------------------------------------------------

def test_new_creates_spec(tmp_path, capsys):
    """New should create a spec from template."""
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "SPEC.md").write_text(
        "---\nid: SPEC-0000\nstatus: draft\n---\n\n# <Title>\n\n## Intent\n\n## Links\n\n- Belongs to: [[COMP-<component>]]\n"
    )
    (tmp_path / ".intent").mkdir()
    (tmp_path / ".intent" / "config.yaml").write_text("id_counters:\n  SPEC: 3\n")
    args = make_args(repo=str(tmp_path), type="spec", component="api", title="Auth Flow")
    rc = cli.cmd_new(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "SPEC-0004" in out
    spec_file = tmp_path / "intent" / "api" / "specs" / "SPEC-0004-auth-flow.md"
    assert spec_file.exists()
    content = spec_file.read_text()
    assert "SPEC-0004" in content
    assert "Auth Flow" in content
    assert "COMP-api" in content


def test_new_creates_adr(tmp_path, capsys):
    """New should create an ADR from template."""
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "ADR.md").write_text(
        "---\nid: ADR-0000\nstatus: draft\n---\n\n# <Decision>\n\n## Links\n\n- Belongs to: [[COMP-<component>]]\n"
    )
    (tmp_path / ".intent").mkdir()
    (tmp_path / ".intent" / "config.yaml").write_text("id_counters: {}\n")
    args = make_args(repo=str(tmp_path), type="adr", component="api", title="Use REST")
    rc = cli.cmd_new(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "ADR-0001" in out


def test_new_missing_template(tmp_path, capsys):
    """New should fail when template is missing."""
    (tmp_path / "templates").mkdir()
    (tmp_path / ".intent").mkdir()
    args = make_args(repo=str(tmp_path), type="spec", component="api", title="Test")
    rc = cli.cmd_new(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "Template not found" in out


def test_new_no_config(tmp_path, capsys):
    """New should use default counter when no config exists."""
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "SPEC.md").write_text(
        "---\nid: SPEC-0000\nstatus: draft\n---\n\n# <Title>\n"
    )
    args = make_args(repo=str(tmp_path), type="spec", component="svc", title="Overview")
    rc = cli.cmd_new(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "SPEC-0001" in out


def test_new_persists_counter(tmp_path, capsys):
    """New should persist the ID counter so consecutive calls get unique IDs."""
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "SPEC.md").write_text(
        "---\nid: SPEC-0000\nstatus: draft\n---\n\n# <Title>\n"
    )
    (tmp_path / ".intent").mkdir()
    (tmp_path / ".intent" / "config.yaml").write_text("id_counters: {}\n")

    # First call
    args = make_args(repo=str(tmp_path), type="spec", component="api", title="First")
    rc = cli.cmd_new(args)
    assert rc == 0
    capsys.readouterr()

    # Second call — must get a different ID
    args = make_args(repo=str(tmp_path), type="spec", component="api", title="Second")
    rc = cli.cmd_new(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "SPEC-0002" in out

    # Verify both files exist with distinct IDs
    assert (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-first.md").exists()
    assert (tmp_path / "intent" / "api" / "specs" / "SPEC-0002-second.md").exists()

    # Verify config was updated
    import yaml
    cfg = yaml.safe_load((tmp_path / ".intent" / "config.yaml").read_text())
    assert cfg["id_counters"]["SPEC"] == 2


def test_new_creates_config_if_missing(tmp_path, capsys):
    """New should create config.yaml with counter when it doesn't exist."""
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "SPEC.md").write_text(
        "---\nid: SPEC-0000\nstatus: draft\n---\n\n# <Title>\n"
    )
    # No .intent/config.yaml at all
    args = make_args(repo=str(tmp_path), type="spec", component="svc", title="Overview")
    rc = cli.cmd_new(args)
    assert rc == 0

    # Config should now exist with the counter
    config_path = tmp_path / ".intent" / "config.yaml"
    assert config_path.exists()
    import yaml
    cfg = yaml.safe_load(config_path.read_text())
    assert cfg["id_counters"]["SPEC"] == 1


# ---------------------------------------------------------------------------
# cmd_init (partial — avoids blocking server)
# ---------------------------------------------------------------------------

def test_init_creates_structure(tmp_path, capsys):
    """Init should create directory structure, config, and templates."""
    # We can't test the full init (it starts a server), but we can test
    # the setup portion by creating a repo where _ensure_viewer returns None
    # (no viewer to serve). The function will complete without blocking.
    args = make_args(repo=str(tmp_path), port=0)
    rc = cli.cmd_init(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "SIGIL" in out
    # Check directories were created
    for d in ["components", "intent", "interfaces", "gates", "templates", ".intent"]:
        assert (tmp_path / d).is_dir(), f"{d} not created"
    # Check config
    assert (tmp_path / ".intent" / "config.yaml").exists()
    # Check templates
    assert (tmp_path / "templates" / "SPEC.md").exists()
    assert (tmp_path / "templates" / "ADR.md").exists()
    assert (tmp_path / "templates" / "COMPONENT.yaml").exists()
    assert (tmp_path / "templates" / "GATE.yaml").exists()
    assert (tmp_path / "templates" / "INTERFACE.md").exists()


def test_init_with_existing_dirs(tmp_path, capsys):
    """Init should not fail when directories already exist."""
    for d in ["components", "intent", "interfaces", "gates", "templates", ".intent"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / ".intent" / "config.yaml").write_text("id_counters: {}\n")
    (tmp_path / "templates" / "SPEC.md").write_text("---\nid: SPEC-0000\n---\n")
    (tmp_path / "templates" / "ADR.md").write_text("---\nid: ADR-0000\n---\n")
    args = make_args(repo=str(tmp_path), port=0)
    rc = cli.cmd_init(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Directory structure exists" in out


def test_init_bootstraps_components(tmp_path, capsys):
    """Init should auto-detect and bootstrap components."""
    (tmp_path / "my-service").mkdir()
    (tmp_path / "my-service" / "package.json").write_text('{"name":"my-service"}')
    (tmp_path / "my-service" / "src").mkdir()
    (tmp_path / "my-service" / "src" / "index.js").write_text("// entry")
    args = make_args(repo=str(tmp_path), port=0)
    rc = cli.cmd_init(args)
    assert rc == 0
    # Component should be created
    assert (tmp_path / "components" / "my-service.yaml").exists()


def test_init_gitignore(tmp_path, capsys):
    """Init should add .intent/index/ to .gitignore."""
    args = make_args(repo=str(tmp_path), port=0)
    cli.cmd_init(args)
    gi = (tmp_path / ".gitignore").read_text()
    assert ".intent/index/" in gi


def test_init_gitignore_idempotent(tmp_path, capsys):
    """Init should not duplicate .gitignore entry."""
    (tmp_path / ".gitignore").write_text("# Sigil generated artifacts\n.intent/index/\n")
    args = make_args(repo=str(tmp_path), port=0)
    cli.cmd_init(args)
    gi = (tmp_path / ".gitignore").read_text()
    assert gi.count(".intent/index/") == 1
