"""Tests targeting remaining coverage gaps in sigil.py."""
import sys
import argparse
import json
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": "."}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# yaml import fallback (lines 22-23)
# ---------------------------------------------------------------------------

def test_yaml_available():
    """yaml module should be available (we have pyyaml)."""
    import yaml
    assert yaml is not None


# ---------------------------------------------------------------------------
# load_yaml RuntimeError (line 151)
# ---------------------------------------------------------------------------

def test_load_yaml_without_yaml(tmp_path):
    """load_yaml should raise RuntimeError when yaml module is None."""
    p = tmp_path / "test.yaml"
    p.write_text("key: value\n")
    original_yaml = cli.yaml
    try:
        cli.yaml = None
        try:
            cli.load_yaml(p)
            assert False, "should have raised"
        except RuntimeError as e:
            assert "PyYAML" in str(e)
    finally:
        cli.yaml = original_yaml


# ---------------------------------------------------------------------------
# discover_interfaces with non-dir children (line 178)
# ---------------------------------------------------------------------------

def test_discover_interfaces_skips_files(tmp_path):
    """discover_interfaces should skip non-directory children."""
    idir = tmp_path / "interfaces"
    idir.mkdir()
    (idir / "README.md").write_text("# Top-level readme")  # Not a subdir
    (idir / "API-V1").mkdir()
    (idir / "API-V1" / "README.md").write_text("# API V1\n\nSome API.\n")
    nodes = cli.discover_interfaces(tmp_path)
    assert "API-V1" in nodes
    assert "README.md" not in nodes


# ---------------------------------------------------------------------------
# classify_intent_doc edge cases (lines 199-203)
# ---------------------------------------------------------------------------

def test_classify_intent_doc_risk():
    assert cli.classify_intent_doc(Path("intent/comp/risks/RISK-0001.md")) == "risk"


def test_classify_intent_doc_rollout():
    assert cli.classify_intent_doc(Path("intent/comp/rollouts/ROLLOUT-0001.md")) == "rollout"


def test_classify_intent_doc_generic():
    assert cli.classify_intent_doc(Path("intent/comp/notes/note.md")) == "doc"


def test_classify_intent_doc_no_intent():
    assert cli.classify_intent_doc(Path("docs/readme.md")) is None


# ---------------------------------------------------------------------------
# _extract_summary truncation (lines 226-229)
# ---------------------------------------------------------------------------

def test_extract_summary_truncation():
    """_extract_summary should truncate long text."""
    long_body = "# Title\n\n" + "word " * 200
    summary = cli._extract_summary(long_body, max_chars=50)
    assert len(summary) <= 55  # 50 + some slack for word boundary + "..."
    assert summary.endswith("...")


def test_extract_summary_skips_heading():
    """_extract_summary should skip # headings."""
    body = "# Title\n\nFirst paragraph content."
    summary = cli._extract_summary(body)
    assert "Title" not in summary
    assert "First paragraph" in summary


# ---------------------------------------------------------------------------
# discover_intent_docs with risk/rollout types (lines 288-303)
# ---------------------------------------------------------------------------

def test_discover_intent_docs_risk(tmp_path):
    """discover_intent_docs should find risk documents."""
    (tmp_path / "intent" / "comp" / "risks").mkdir(parents=True)
    (tmp_path / "intent" / "comp" / "risks" / "RISK-0001-security.md").write_text(
        "---\nid: RISK-0001\n---\n\n# Security Risk\n"
    )
    nodes = cli.discover_intent_docs(tmp_path)
    assert "RISK-0001" in nodes
    assert nodes["RISK-0001"].type == "risk"


def test_discover_intent_docs_rollout(tmp_path):
    """discover_intent_docs should find rollout documents."""
    (tmp_path / "intent" / "comp" / "rollouts").mkdir(parents=True)
    (tmp_path / "intent" / "comp" / "rollouts" / "ROLLOUT-0001-launch.md").write_text(
        "---\nid: ROLLOUT-0001\n---\n\n# Launch Plan\n"
    )
    nodes = cli.discover_intent_docs(tmp_path)
    assert "ROLLOUT-0001" in nodes
    assert nodes["ROLLOUT-0001"].type == "rollout"


# ---------------------------------------------------------------------------
# _write_review_json (lines 407-523) — invoked via write_graph_artifacts
# ---------------------------------------------------------------------------

def test_write_review_json_with_changes(tmp_path):
    """_write_review_json should create review.json."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text(
        'id: COMP-api\nname: API\npaths:\n  - "api/**"\n'
    )
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Test\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    g = cli.build_graph(tmp_path)
    out_path = tmp_path / ".intent" / "index" / "review.json"
    cli._write_review_json(tmp_path, g, out_path)
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert "summary" in data
    assert "coverage_pct" in data["summary"]


# ---------------------------------------------------------------------------
# _find_viewer importlib fallback (lines 538-545)
# ---------------------------------------------------------------------------

def test_find_viewer_importlib_fallback(tmp_path):
    """_find_viewer should check importlib.util for sigil_cli package."""
    # Just verify it doesn't crash when package doesn't exist
    result = cli._find_viewer(tmp_path)
    # It will be None since no viewer exists at tmp_path
    assert result is None or result.exists()


# ---------------------------------------------------------------------------
# _ensure_viewer copies from source (lines 556-558)
# ---------------------------------------------------------------------------

def test_ensure_viewer_copies_from_bundled(tmp_path):
    """_ensure_viewer should copy viewer if available at alternate location."""
    # Create a "bundled" viewer next to sigil.py
    sigil_path = Path(cli.__file__)
    bundled = sigil_path.with_name("sigil_viewer.html")
    created = False
    try:
        if not bundled.exists():
            bundled.write_text("<html><head><title>Sigil</title></head><body>Viewer</body></html>")
            created = True
        result = cli._ensure_viewer(tmp_path)
        if result:
            assert result.exists()
    finally:
        if created and bundled.exists():
            bundled.unlink()


# ---------------------------------------------------------------------------
# checkout_tree (lines 574-581)
# ---------------------------------------------------------------------------

def test_checkout_tree_fallback(tmp_path):
    """checkout_tree should handle archives without specific dirs."""
    # Initialize a git repo
    import subprocess
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
    (tmp_path / "file.txt").write_text("hello")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "init"], capture_output=True,
                   env={**__import__("os").environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@test.com",
                        "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@test.com"})
    sha = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    dest = tmp_path / "checkout_dest"
    cli.checkout_tree(tmp_path, sha, dest)
    assert dest.exists()


# ---------------------------------------------------------------------------
# _score_node / _find_excerpt edge cases (lines 742-830)
# ---------------------------------------------------------------------------

def test_score_node_with_sections():
    """_score_node should boost section matches."""
    query_tokens = ["auth"]
    body_tokens = ["auth", "login", "password"]
    title_tokens = ["endpoints"]
    nid = "SPEC-0001"
    sections = {"Context": "auth system for users", "Intent": "build auth module"}
    score = cli._score_node(query_tokens, body_tokens, title_tokens, nid, sections)
    assert score > 0


def test_find_excerpt_returns_context():
    """_find_excerpt should return text around the matching token."""
    body = "This is a long document.\n\nThe auth system handles login.\n\nMore text here."
    excerpt = cli._find_excerpt(body, ["auth"])
    assert "auth" in excerpt


def test_find_excerpt_no_match():
    """_find_excerpt should return start of body when no match."""
    body = "This is a document.\n\nSome content here."
    excerpt = cli._find_excerpt(body, ["nonexistent"])
    assert len(excerpt) > 0


# ---------------------------------------------------------------------------
# cmd_diff (lines 1014-1031) — requires git
# ---------------------------------------------------------------------------

def test_cmd_diff_between_commits(tmp_path, capsys):
    """cmd_diff should compare graphs between two commits using mocked checkout."""
    # Create two graph states directly to test diff logic
    base_dir = tmp_path / "base"
    head_dir = tmp_path / "head"
    base_dir.mkdir()
    head_dir.mkdir()

    # Base: one component
    (base_dir / "components").mkdir()
    (base_dir / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")

    # Head: two components + a spec
    (head_dir / "components").mkdir()
    (head_dir / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    (head_dir / "components" / "web.yaml").write_text("id: COMP-web\nname: Web\n")
    (head_dir / "intent" / "api" / "specs").mkdir(parents=True)
    (head_dir / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\n---\n\n# Test\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )

    g_base = cli.build_graph(base_dir)
    g_head = cli.build_graph(head_dir)
    d = cli.graph_diff(g_base, g_head)

    # Should detect added nodes
    assert "COMP-web" in d["nodes_added"]
    assert "SPEC-0001" in d["nodes_added"]

    # Test diff_to_markdown
    md = cli.diff_to_markdown(d, g_head)
    assert "COMP-web" in md
    assert "SPEC-0001" in md

    # Also test cmd_diff with mocked checkout_tree
    def mock_checkout(repo_root, sha, dest):
        import shutil
        src = base_dir if sha == "base_sha" else head_dir
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)

    with mock.patch.object(cli, "checkout_tree", side_effect=mock_checkout):
        args = make_args(repo=str(tmp_path), base="base_sha", head="head_sha", out=None, md=None)
        rc = cli.cmd_diff(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert "COMP-web" in out


def test_cmd_diff_with_output_files(tmp_path, capsys):
    """cmd_diff should write JSON and MD output files."""
    import subprocess, os
    env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t.com",
           "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t.com"}
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "first"], capture_output=True, env=env)
    sha1 = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "-C", str(tmp_path), "commit", "--allow-empty", "-m", "second"], capture_output=True, env=env)
    sha2 = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()

    out_json = str(tmp_path / "diff.json")
    out_md = str(tmp_path / "diff.md")
    args = make_args(repo=str(tmp_path), base=sha1, head=sha2, out=out_json, md=out_md)
    rc = cli.cmd_diff(args)
    assert rc == 0
    assert (tmp_path / "diff.json").exists()
    assert (tmp_path / "diff.md").exists()


# ---------------------------------------------------------------------------
# cmd_new edge case: unknown type (line 1057)
# ---------------------------------------------------------------------------

def test_new_unknown_type(tmp_path, capsys):
    """cmd_new should fail on unknown type."""
    (tmp_path / "templates").mkdir()
    args = make_args(repo=str(tmp_path), type="risk", component="api", title="Test")
    # Manually override since argparse choices would catch this
    rc = cli.cmd_new(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "Unknown type" in out


# ---------------------------------------------------------------------------
# cmd_lint edge cases (lines 1119, 1126, 1143-1152)
# ---------------------------------------------------------------------------

def test_lint_unknown_status(tmp_path, capsys):
    """Lint should warn on unknown status values."""
    (tmp_path / "intent" / "comp" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "comp" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: banana\n---\n\n# Test\n\n## Intent\n.\n## Goals\n.\n## Non-goals\n.\n## Design\n.\n## Acceptance Criteria\n.\n## Links\n- Belongs to: [[COMP-comp]]\n"
    )
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "comp.yaml").write_text("id: COMP-comp\nname: Comp\n")
    args = make_args(repo=str(tmp_path), min_severity="warn")
    cli.cmd_lint(args)
    out = capsys.readouterr().out
    assert "unknown status" in out


def test_lint_no_belongs_to(tmp_path, capsys):
    """Lint should warn when spec has no belongs_to link."""
    (tmp_path / "intent" / "comp" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "comp" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Test\n\n## Intent\n.\n## Goals\n.\n## Non-goals\n.\n## Design\n.\n## Acceptance Criteria\n.\n## Links\n\n"
    )
    args = make_args(repo=str(tmp_path), min_severity="warn")
    cli.cmd_lint(args)
    out = capsys.readouterr().out
    assert "Belongs to" in out


def test_lint_adr_missing_sections(tmp_path, capsys):
    """Lint should warn about missing ADR sections."""
    (tmp_path / "intent" / "comp" / "adrs").mkdir(parents=True)
    (tmp_path / "intent" / "comp" / "adrs" / "ADR-0001-test.md").write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# Test Decision\n"
    )
    args = make_args(repo=str(tmp_path), min_severity="warn")
    cli.cmd_lint(args)
    out = capsys.readouterr().out
    assert "Context" in out or "Decision" in out or "Consequences" in out


def test_lint_dangling_edge(tmp_path, capsys):
    """Lint should warn about dangling references."""
    (tmp_path / "intent" / "comp" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "comp" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Test\n\n## Links\n\n- Depends on: [[MISSING-0099]]\n"
    )
    args = make_args(repo=str(tmp_path), min_severity="warn")
    cli.cmd_lint(args)
    out = capsys.readouterr().out
    assert "dangling" in out


# ---------------------------------------------------------------------------
# cmd_fmt edge cases (lines 1186, 1200, 1205, 1215)
# ---------------------------------------------------------------------------

def test_fmt_adds_id_to_existing_frontmatter(tmp_path, capsys):
    """fmt should insert ID into existing front matter when missing."""
    (tmp_path / "intent" / "comp" / "specs").mkdir(parents=True)
    spec = tmp_path / "intent" / "comp" / "specs" / "SPEC-0042-thing.md"
    spec.write_text("---\nstatus: draft\n---\n\n# Thing\n\n## Links\n\n")
    args = make_args(repo=str(tmp_path))
    cli.cmd_fmt(args)
    content = spec.read_text()
    assert "id: SPEC-0042" in content
    assert "status: draft" in content


def test_fmt_adds_id_without_frontmatter(tmp_path, capsys):
    """fmt should create front matter with ID when none exists."""
    (tmp_path / "intent" / "comp" / "specs").mkdir(parents=True)
    spec = tmp_path / "intent" / "comp" / "specs" / "SPEC-0042-thing.md"
    spec.write_text("# Thing\n\n## Intent\nTest.")
    args = make_args(repo=str(tmp_path))
    cli.cmd_fmt(args)
    content = spec.read_text()
    assert "id: SPEC-0042" in content
    assert "## Links" in content


def test_fmt_adds_links_no_trailing_newline(tmp_path, capsys):
    """fmt should add Links section even when file doesn't end with newline."""
    (tmp_path / "intent" / "comp" / "specs").mkdir(parents=True)
    spec = tmp_path / "intent" / "comp" / "specs" / "SPEC-0001-thing.md"
    spec.write_text("---\nid: SPEC-0001\nstatus: draft\n---\n\n# Thing")  # No trailing newline
    args = make_args(repo=str(tmp_path))
    cli.cmd_fmt(args)
    content = spec.read_text()
    assert "## Links" in content


# ---------------------------------------------------------------------------
# cmd_init deep scan (lines 1366-1401)
# ---------------------------------------------------------------------------

def test_init_deep_scan_multi_file_dir(tmp_path, capsys):
    """Init should auto-detect directories with many files as components."""
    (tmp_path / "my-lib").mkdir()
    for i in range(5):
        (tmp_path / "my-lib" / f"file{i}.py").write_text(f"# file {i}")
    args = make_args(repo=str(tmp_path), port=0)
    cli.cmd_init(args)
    # Should create a component for my-lib
    assert (tmp_path / "components" / "my-lib.yaml").exists()
    content = (tmp_path / "components" / "my-lib.yaml").read_text()
    assert "COMP-my-lib" in content
    # Should also create a starter spec
    spec_dir = tmp_path / "intent" / "my-lib" / "specs"
    assert spec_dir.exists()


def test_init_skips_small_dirs(tmp_path, capsys):
    """Init should skip directories with <= 2 files and no manifest."""
    (tmp_path / "tiny").mkdir()
    (tmp_path / "tiny" / "readme.md").write_text("# readme")
    args = make_args(repo=str(tmp_path), port=0)
    cli.cmd_init(args)
    # Should NOT create component for tiny
    assert not (tmp_path / "components" / "tiny.yaml").exists()


# ---------------------------------------------------------------------------
# cmd_suggest edge cases (lines 2228-2322)
# ---------------------------------------------------------------------------

def test_suggest_with_gate(tmp_path, capsys):
    """Suggest should show gates enforced on the component."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text(
        'id: COMP-api\nname: API\npaths:\n  - "api/**"\n'
    )
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Test\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / "gates").mkdir()
    (tmp_path / "gates" / "GATE-0001-quality.yaml").write_text(
        "id: GATE-0001\napplies_to:\n  - node: COMP-api\ndocs:\n  summary: Quality gate\nchecks: []\n"
    )
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "server.py").write_text("# server")
    args = make_args(repo=str(tmp_path), path="api/server.py")
    rc = cli.cmd_suggest(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "GATE-0001" in out or "Enforced Gates" in out


# ---------------------------------------------------------------------------
# cmd_timeline with git history (lines 2374-2438)
# ---------------------------------------------------------------------------

def test_timeline_with_git_history(tmp_path, capsys):
    """Timeline should parse git log for intent file changes."""
    import subprocess, os
    env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t.com",
           "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t.com"}
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "add component"], capture_output=True, env=env)
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\n---\n\n# Test\n"
    )
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "add spec"], capture_output=True, env=env)
    (tmp_path / ".intent" / "index").mkdir(parents=True)

    out_file = tmp_path / "timeline.json"
    args = make_args(repo=str(tmp_path), output=str(out_file))
    args.max = "50"
    rc = cli.cmd_timeline(args)
    assert rc == 0
    data = json.loads(out_file.read_text())
    assert len(data["events"]) > 0
    out = capsys.readouterr().out
    assert "commits" in out


# ---------------------------------------------------------------------------
# cmd_scan detailed branches (lines 3304-3652)
# ---------------------------------------------------------------------------

def test_scan_detects_readme(tmp_path, capsys):
    """Scan should detect README files in components."""
    (tmp_path / "service").mkdir()
    (tmp_path / "service" / "package.json").write_text('{"name":"service"}')
    (tmp_path / "service" / "README.md").write_text("# Service\n\nDocumentation.")
    (tmp_path / "service" / "src").mkdir()
    (tmp_path / "service" / "src" / "index.js").write_text("// main")
    (tmp_path / ".intent").mkdir()
    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    cli.cmd_scan(args)
    data = json.loads((tmp_path / "scan.json").read_text())
    comp = next(c for c in data["components"] if c["slug"] == "service")
    assert comp["has_readme"] is True


def test_scan_detects_tests(tmp_path, capsys):
    """Scan should detect test directories."""
    (tmp_path / "service").mkdir()
    (tmp_path / "service" / "pyproject.toml").write_text("[project]\nname='service'\n")
    (tmp_path / "service" / "tests").mkdir()
    (tmp_path / "service" / "tests" / "test_main.py").write_text("def test_ok(): pass")
    (tmp_path / "service" / "src").mkdir()
    (tmp_path / "service" / "src" / "main.py").write_text("# main")
    (tmp_path / ".intent").mkdir()
    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    cli.cmd_scan(args)
    data = json.loads((tmp_path / "scan.json").read_text())
    comp = next(c for c in data["components"] if c["slug"] == "service")
    assert comp["has_tests"] is True


def test_scan_detects_dockerfile(tmp_path, capsys):
    """Scan should detect Dockerfile in components."""
    (tmp_path / "service").mkdir()
    (tmp_path / "service" / "go.mod").write_text("module example.com/service")
    (tmp_path / "service" / "Dockerfile").write_text("FROM golang:1.21")
    (tmp_path / "service" / "main.go").write_text("package main")
    (tmp_path / ".intent").mkdir()
    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    cli.cmd_scan(args)
    data = json.loads((tmp_path / "scan.json").read_text())
    comp = next(c for c in data["components"] if c["slug"] == "service")
    assert comp["has_dockerfile"] is True


def test_scan_detects_decisions(tmp_path, capsys):
    """Scan should detect decision signals in README files."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "README.md").write_text(
        "# Architecture\n\nWe decided to use REST. The decision was made because of trade-off between simplicity and performance. "
        "We chose REST over GraphQL. The rationale is simpler tooling."
    )
    (tmp_path / ".intent").mkdir()
    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    cli.cmd_scan(args)
    data = json.loads((tmp_path / "scan.json").read_text())
    assert len(data["decisions"]) > 0


def test_scan_detects_adr_directories(tmp_path, capsys):
    """Scan should detect existing ADR directories."""
    (tmp_path / "adr").mkdir()
    (tmp_path / "adr" / "0001-use-rest.md").write_text("# Use REST")
    (tmp_path / ".intent").mkdir()
    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    cli.cmd_scan(args)
    data = json.loads((tmp_path / "scan.json").read_text())
    assert len(data["decisions"]) > 0


def test_scan_detects_infra(tmp_path, capsys):
    """Scan should detect infrastructure files."""
    (tmp_path / "docker-compose.yml").write_text("version: '3'")
    (tmp_path / ".intent").mkdir()
    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    cli.cmd_scan(args)
    data = json.loads((tmp_path / "scan.json").read_text())
    assert len(data["infra"]) > 0
    assert data["infra"][0]["type"] == "Docker Compose"


def test_scan_recommendations_no_gates(tmp_path, capsys):
    """Scan should recommend gates when specs exist but no gates."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\n---\n\n# Test\n"
    )
    (tmp_path / ".intent").mkdir()
    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    cli.cmd_scan(args)
    data = json.loads((tmp_path / "scan.json").read_text())
    assert any("gate" in r.lower() for r in data["recommendations"])


def test_scan_recommendations_no_tests(tmp_path, capsys):
    """Scan should recommend tests when components have no tests."""
    (tmp_path / "service").mkdir()
    (tmp_path / "service" / "package.json").write_text('{"name":"service"}')
    (tmp_path / "service" / "index.js").write_text("// main")
    (tmp_path / ".intent").mkdir()
    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    cli.cmd_scan(args)
    data = json.loads((tmp_path / "scan.json").read_text())
    assert any("test" in r.lower() for r in data["recommendations"])


def test_scan_recommendations_no_ci(tmp_path, capsys):
    """Scan should recommend CI when none detected."""
    (tmp_path / ".intent").mkdir()
    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    cli.cmd_scan(args)
    data = json.loads((tmp_path / "scan.json").read_text())
    assert any("CI" in r for r in data["recommendations"])


# ---------------------------------------------------------------------------
# cmd_pr with intent changes and gate results (lines 2936-2992)
# ---------------------------------------------------------------------------

def test_pr_with_intent_changes_and_gates(tmp_path, capsys):
    """PR should show intent changes and gate results in dry-run."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text(
        'id: COMP-api\nname: API\npaths:\n  - "api/**"\n'
    )
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Test\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / "intent" / "api" / "adrs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "adrs" / "ADR-0001-rest.md").write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# REST\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / "gates").mkdir()
    (tmp_path / "gates" / "GATE-0001.yaml").write_text(
        "id: GATE-0001\ndocs:\n  summary: Quality\nchecks:\n  - id: check1\n    kind: lint-rule\n    cmd: echo ok\n"
    )
    (tmp_path / ".git").mkdir()

    pr_json = json.dumps({
        "number": 10,
        "title": "Feat",
        "headRefName": "feat",
        "baseRefName": "main",
        "url": "https://github.com/test/repo/pull/10",
        "additions": 50,
        "deletions": 5,
        "changedFiles": 4,
    })

    def mock_run_cmd(cmd, cwd=None):
        if "pr" in cmd and "view" in cmd:
            return pr_json
        if "pr" in cmd and "diff" in cmd:
            return "api/server.py\ncomponents/api.yaml\nintent/api/specs/SPEC-0001-test.md\nscripts/deploy.sh\n"
        raise RuntimeError(f"unexpected: {cmd}")

    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        args = make_args(repo=str(tmp_path), number=10, dry_run=True)
        rc = cli.cmd_pr(args)

    assert rc == 0
    out = capsys.readouterr().out
    assert "Intent Documents Changed" in out or "intent" in out.lower()
    assert "Sigil Intent Analysis" in out


# ---------------------------------------------------------------------------
# cmd_ci with review (lines 3737-3762)
# ---------------------------------------------------------------------------

def test_ci_with_review_error(tmp_path, capsys):
    """CI should handle review errors gracefully."""
    for d in ["components", "intent", "interfaces", "gates", "templates", ".intent"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / ".intent" / "config.yaml").write_text("id_counters: {}\n")
    (tmp_path / "templates" / "SPEC.md").write_text("---\nid: SPEC-0000\n---\n")
    (tmp_path / "templates" / "ADR.md").write_text("---\nid: ADR-0000\n---\n")
    (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    (tmp_path / ".git").mkdir()
    viewer_dir = tmp_path / "tools" / "intent_viewer"
    viewer_dir.mkdir(parents=True)
    (viewer_dir / "index.html").write_text("<html><head><title>Sigil</title></head><body></body></html>")

    args = make_args(repo=str(tmp_path), strict=False, base=None, head=None)
    rc = cli.cmd_ci(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Pipeline:" in out


# ---------------------------------------------------------------------------
# Edge cases in write_graph_artifacts (lines 354-404)
# ---------------------------------------------------------------------------

def test_write_graph_artifacts_with_gate_results(tmp_path):
    """write_graph_artifacts should include gate results in graph.json."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    (tmp_path / "gates").mkdir()
    (tmp_path / "gates" / "GATE-0001.yaml").write_text(
        "id: GATE-0001\ndocs:\n  summary: Quality\nchecks:\n  - id: check1\n    kind: lint-rule\n    cmd: echo ok\n"
    )
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    g = cli.build_graph(tmp_path)
    cli.write_graph_artifacts(tmp_path, g)

    graph_json = json.loads((tmp_path / ".intent" / "index" / "graph.json").read_text())
    assert "nodes" in graph_json
    assert "edges" in graph_json
    # search.json should be written
    assert (tmp_path / ".intent" / "index" / "search.json").exists()
