"""Tests for cmd_pr (dry-run), cmd_doctor, cmd_ci, cmd_hook, diff_to_markdown, main()."""
import sys
import argparse
import json
import subprocess
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": "."}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _setup_full_repo(tmp_path):
    """Create a fully populated repo for PR/CI tests."""
    for d in ["components", "intent", "interfaces", "gates", "templates", ".intent", ".intent/index"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / ".intent" / "config.yaml").write_text("id_counters: {}\n")
    (tmp_path / "templates" / "SPEC.md").write_text("---\nid: SPEC-0000\n---\n")
    (tmp_path / "templates" / "ADR.md").write_text("---\nid: ADR-0000\n---\n")
    (tmp_path / "components" / "api.yaml").write_text(
        'id: COMP-api\nname: API\npaths:\n  - "api/**"\n'
    )
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Test\n\n## Intent\n.\n## Goals\n.\n## Non-goals\n.\n## Design\n.\n## Acceptance Criteria\n.\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / ".git").mkdir()
    # Create viewer for export
    viewer_dir = tmp_path / "tools" / "intent_viewer"
    viewer_dir.mkdir(parents=True)
    (viewer_dir / "index.html").write_text(
        "<html><head><title>Sigil Viewer</title></head><body>Viewer</body></html>"
    )


# ---------------------------------------------------------------------------
# cmd_hook
# ---------------------------------------------------------------------------

def test_hook_status_not_installed(tmp_path, capsys):
    """Hook status should report not installed."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    args = make_args(repo=str(tmp_path), action="status")
    rc = cli.cmd_hook(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "not installed" in out


def test_hook_status_installed(tmp_path, capsys):
    """Hook status should report installed when hook exists."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.write_text("#!/bin/sh\n# Sigil intent coverage check\nsigil review --staged\nexit 0\n")
    args = make_args(repo=str(tmp_path), action="status")
    rc = cli.cmd_hook(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "installed" in out


def test_hook_install_no_git(tmp_path, capsys):
    """Hook install should fail when no .git/hooks directory."""
    args = make_args(repo=str(tmp_path), action="install")
    rc = cli.cmd_hook(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "Not a git repository" in out


def test_hook_uninstall_no_hook(tmp_path, capsys):
    """Hook uninstall should be fine when no hook exists."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    args = make_args(repo=str(tmp_path), action="uninstall")
    rc = cli.cmd_hook(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No pre-commit hook found" in out


def test_hook_uninstall_not_sigil(tmp_path, capsys):
    """Hook uninstall should be fine when hook exists but isn't sigil."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.write_text("#!/bin/sh\necho 'other hook'\n")
    args = make_args(repo=str(tmp_path), action="uninstall")
    rc = cli.cmd_hook(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Sigil hook not found" in out


def test_hook_uninstall_removes_sigil_section(tmp_path, capsys):
    """Hook uninstall should remove the sigil section from a multi-hook file."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.write_text("#!/bin/sh\necho 'other hook'\n\n# Sigil intent coverage check\nsigil review --staged\nexit 0\n")
    hook_path.chmod(0o755)
    args = make_args(repo=str(tmp_path), action="uninstall")
    rc = cli.cmd_hook(args)
    assert rc == 0
    content = hook_path.read_text()
    assert "Sigil" not in content
    assert "other hook" in content


def test_hook_uninstall_removes_file_if_only_sigil(tmp_path, capsys):
    """Hook uninstall should remove the file entirely if only sigil content."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.write_text("#!/bin/sh\n\n# Sigil intent coverage check\nsigil review --staged\nexit 0\n")
    hook_path.chmod(0o755)
    args = make_args(repo=str(tmp_path), action="uninstall")
    rc = cli.cmd_hook(args)
    assert rc == 0
    assert not hook_path.exists()


def test_hook_invalid_action(tmp_path):
    """Hook with invalid action should return 1."""
    args = make_args(repo=str(tmp_path), action="invalid")
    rc = cli.cmd_hook(args)
    assert rc == 1


# ---------------------------------------------------------------------------
# diff_to_markdown edge cases
# ---------------------------------------------------------------------------

def test_diff_to_markdown_all_sections():
    """diff_to_markdown should render all sections when present."""
    g = cli.Graph(
        nodes={"A": cli.Node(id="A", type="spec", title="Title A", path="a.md")},
        edges=[]
    )
    d = {
        "nodes_added": ["A"],
        "nodes_removed": ["B"],
        "nodes_changed": ["A"],
        "edges_added": [{"type": "belongs_to", "src": "A", "dst": "C"}],
        "edges_removed": [{"type": "decided_by", "src": "A", "dst": "D"}],
    }
    md = cli.diff_to_markdown(d, g)
    assert "## Intent Graph Diff" in md
    assert "Nodes added" in md
    assert "Nodes removed" in md
    assert "Nodes changed" in md
    assert "Edges added" in md
    assert "Edges removed" in md


def test_diff_to_markdown_empty():
    """diff_to_markdown should render header even with empty diff."""
    g = cli.Graph(nodes={}, edges=[])
    d = {
        "nodes_added": [],
        "nodes_removed": [],
        "nodes_changed": [],
        "edges_added": [],
        "edges_removed": [],
    }
    md = cli.diff_to_markdown(d, g)
    assert "## Intent Graph Diff" in md
    assert "No" in md and "change" in md.lower()


# ---------------------------------------------------------------------------
# cmd_doctor
# ---------------------------------------------------------------------------

def test_doctor_full_repo(tmp_path, capsys):
    """Doctor on a well-set-up repo should pass most checks."""
    _setup_full_repo(tmp_path)
    # Build index
    g = cli.build_graph(tmp_path)
    cli.write_graph_artifacts(tmp_path, g)
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_doctor(args)
    out = capsys.readouterr().out
    assert "Sigil Doctor" in out
    assert "passed" in out
    # Should pass most checks
    assert "Directory structure" in out
    assert "Config file" in out
    assert "Templates" in out


def test_doctor_missing_everything(tmp_path, capsys):
    """Doctor on empty dir should fail most checks."""
    (tmp_path / ".git").mkdir()
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_doctor(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "failed" in out


def test_doctor_git_repo_in_subdirectory(tmp_path, capsys):
    """Doctor should detect git repo when --repo points to a subdirectory."""
    # Initialize a real git repo at the root
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
    # Create a subdirectory with sigil structure
    sub = tmp_path / "project"
    sub.mkdir()
    _setup_full_repo(sub)
    g = cli.build_graph(sub)
    cli.write_graph_artifacts(sub, g)
    args = make_args(repo=str(sub))
    cli.cmd_doctor(args)
    out = capsys.readouterr().out
    # Git repository check should pass even though .git is in parent
    assert "Git repository" in out
    lines = [l for l in out.splitlines() if "Git repository" in l]
    assert any("ok" in l for l in lines), f"Expected git check to pass: {lines}"


def test_doctor_corrupt_graph_json(tmp_path, capsys):
    """Doctor should detect corrupt graph.json."""
    _setup_full_repo(tmp_path)
    idx = tmp_path / ".intent" / "index"
    idx.mkdir(parents=True, exist_ok=True)
    (idx / "graph.json").write_text("not json {{{")
    args = make_args(repo=str(tmp_path))
    cli.cmd_doctor(args)
    out = capsys.readouterr().out
    assert "corrupt" in out


# ---------------------------------------------------------------------------
# cmd_ci edge cases
# ---------------------------------------------------------------------------

def test_ci_on_full_repo(tmp_path, capsys):
    """CI should pass on a well-set-up repo."""
    _setup_full_repo(tmp_path)
    args = make_args(repo=str(tmp_path), strict=False, base=None, head=None)
    rc = cli.cmd_ci(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Sigil CI Pipeline" in out
    assert "Indexing" in out
    assert "Linting" in out
    assert "Checking gates" in out
    assert "Generating badge" in out
    assert "Pipeline:" in out


def test_ci_strict_with_lint_issues(tmp_path, capsys):
    """CI strict should fail when lint issues exist."""
    for d in ["components", "intent", "interfaces", "gates", "templates", ".intent"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / ".intent" / "config.yaml").write_text("id_counters: {}\n")
    (tmp_path / "templates" / "SPEC.md").write_text("---\nid: SPEC-0000\n---\n")
    (tmp_path / "templates" / "ADR.md").write_text("---\nid: ADR-0000\n---\n")
    # Create a spec with lint errors
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-bad.md").write_text(
        "---\nstatus: accepted\n---\n\n# Bad spec\n"
    )
    (tmp_path / ".git").mkdir()
    viewer_dir = tmp_path / "tools" / "intent_viewer"
    viewer_dir.mkdir(parents=True)
    (viewer_dir / "index.html").write_text("<html><head><title>Sigil</title></head><body></body></html>")
    args = make_args(repo=str(tmp_path), strict=True, base=None, head=None)
    rc = cli.cmd_ci(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAIL" in out


# ---------------------------------------------------------------------------
# cmd_pr (dry run, mocked gh)
# ---------------------------------------------------------------------------

def test_pr_dry_run(tmp_path, capsys):
    """PR dry-run should print comment without posting."""
    _setup_full_repo(tmp_path)
    # Create some "changed" files
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "server.py").write_text("# server")

    pr_json = json.dumps({
        "number": 42,
        "title": "Add auth",
        "headRefName": "feature/auth",
        "baseRefName": "main",
        "url": "https://github.com/test/repo/pull/42",
        "additions": 100,
        "deletions": 10,
        "changedFiles": 5,
    })

    diff_files = "api/server.py\ncomponents/api.yaml\n"

    def mock_run_cmd(cmd, cwd=None):
        if "pr" in cmd and "view" in cmd:
            return pr_json
        if "pr" in cmd and "diff" in cmd:
            return diff_files
        raise RuntimeError(f"unexpected command: {cmd}")

    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        args = make_args(repo=str(tmp_path), number=42, dry_run=True)
        rc = cli.cmd_pr(args)

    assert rc == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "Sigil Intent Analysis" in out
    assert "Intent Coverage" in out
    assert "COMP-api" in out or "Coverage" in out


def test_pr_no_gh_fails(tmp_path, capsys):
    """PR should fail when gh CLI is not available."""
    _setup_full_repo(tmp_path)

    def mock_run_cmd(cmd, cwd=None):
        raise RuntimeError("gh not found")

    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        args = make_args(repo=str(tmp_path), number=None, dry_run=False)
        rc = cli.cmd_pr(args)

    assert rc == 1
    out = capsys.readouterr().out
    assert "Error" in out


def test_pr_with_uncovered_files(tmp_path, capsys):
    """PR should report ungoverned files."""
    _setup_full_repo(tmp_path)

    pr_json = json.dumps({
        "number": 1,
        "title": "Test",
        "headRefName": "feat",
        "baseRefName": "main",
        "url": "https://github.com/test/repo/pull/1",
        "additions": 10,
        "deletions": 0,
        "changedFiles": 2,
    })

    def mock_run_cmd(cmd, cwd=None):
        if "pr" in cmd and "view" in cmd:
            return pr_json
        if "pr" in cmd and "diff" in cmd:
            return "scripts/deploy.sh\napi/server.py\n"
        raise RuntimeError(f"unexpected: {cmd}")

    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        args = make_args(repo=str(tmp_path), number=1, dry_run=True)
        rc = cli.cmd_pr(args)

    assert rc == 0
    out = capsys.readouterr().out
    assert "Ungoverned" in out or "ungoverned" in out.lower() or "Coverage" in out


def test_pr_post_comment_failure(tmp_path, capsys):
    """PR should handle comment post failure gracefully."""
    _setup_full_repo(tmp_path)

    pr_json = json.dumps({
        "number": 5,
        "title": "Test",
        "headRefName": "feat",
        "baseRefName": "main",
        "url": "https://github.com/test/repo/pull/5",
        "additions": 10,
        "deletions": 0,
        "changedFiles": 1,
    })

    call_count = [0]

    def mock_run_cmd(cmd, cwd=None):
        if "pr" in cmd and "view" in cmd:
            return pr_json
        if "pr" in cmd and "diff" in cmd:
            return "api/server.py\n"
        if "pr" in cmd and "comment" in cmd:
            raise RuntimeError("API error")
        raise RuntimeError(f"unexpected: {cmd}")

    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        args = make_args(repo=str(tmp_path), number=5, dry_run=False)
        rc = cli.cmd_pr(args)

    assert rc == 1
    out = capsys.readouterr().out
    assert "Failed to post comment" in out


# ---------------------------------------------------------------------------
# main() / argparse
# ---------------------------------------------------------------------------

def test_main_status(tmp_path, capsys):
    """main() should dispatch to cmd_status."""
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "status"]):
        rc = cli.main()
    assert rc == 0


def test_main_index(tmp_path, capsys):
    """main() should dispatch to cmd_index."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "index"]):
        rc = cli.main()
    assert rc == 0


def test_main_lint(tmp_path, capsys):
    """main() should dispatch to cmd_lint."""
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "lint"]):
        rc = cli.main()
    assert rc == 0


def test_main_badge(tmp_path, capsys):
    """main() should dispatch to cmd_badge."""
    (tmp_path / ".intent").mkdir()
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "badge"]):
        rc = cli.main()
    assert rc == 0


def test_main_doctor(tmp_path, capsys):
    """main() should dispatch to cmd_doctor."""
    (tmp_path / ".git").mkdir()
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "doctor"]):
        rc = cli.main()
    # Will fail some checks on empty repo, that's fine
    assert isinstance(rc, int)


def test_main_map(tmp_path, capsys):
    """main() should dispatch to cmd_map."""
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "map"]):
        rc = cli.main()
    assert rc == 0


def test_main_ask(tmp_path, capsys):
    """main() should dispatch to cmd_ask."""
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "ask", "what is this"]):
        rc = cli.main()
    assert rc == 0


def test_main_scan(tmp_path, capsys):
    """main() should dispatch to cmd_scan."""
    (tmp_path / ".intent").mkdir()
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "scan", "--dry-run"]):
        rc = cli.main()
    assert rc == 0


def test_main_fmt(tmp_path, capsys):
    """main() should dispatch to cmd_fmt."""
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "fmt"]):
        rc = cli.main()
    assert rc == 0


def test_main_bootstrap(tmp_path, capsys):
    """main() should dispatch to cmd_bootstrap."""
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "bootstrap", "--dry-run"]):
        rc = cli.main()
    assert rc == 0


def test_main_check(tmp_path, capsys):
    """main() should dispatch to cmd_check."""
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "check"]):
        rc = cli.main()
    assert rc == 0


def test_main_drift(tmp_path, capsys):
    """main() should dispatch to cmd_drift."""
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "drift"]):
        rc = cli.main()
    assert isinstance(rc, int)


def test_main_suggest(tmp_path, capsys):
    """main() should dispatch to cmd_suggest."""
    (tmp_path / "test.txt").write_text("hello")
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "suggest", "test.txt"]):
        rc = cli.main()
    assert rc == 0


def test_main_why(tmp_path, capsys):
    """main() should dispatch to cmd_why."""
    (tmp_path / "test.txt").write_text("hello")
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "why", "test.txt"]):
        rc = cli.main()
    assert rc == 0


def test_main_timeline(tmp_path, capsys):
    """main() should dispatch to cmd_timeline."""
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "timeline"]):
        rc = cli.main()
    assert rc == 0


def test_main_hook(tmp_path, capsys):
    """main() should dispatch to cmd_hook."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "hook", "status"]):
        rc = cli.main()
    assert rc == 0


def test_main_ci(tmp_path, capsys):
    """main() should dispatch to cmd_ci."""
    for d in ["components", "intent", "interfaces", "gates", "templates", ".intent"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / ".intent" / "config.yaml").write_text("id_counters: {}\n")
    (tmp_path / "templates" / "SPEC.md").write_text("---\nid: SPEC-0000\n---\n")
    (tmp_path / "templates" / "ADR.md").write_text("---\nid: ADR-0000\n---\n")
    with mock.patch("sys.argv", ["sigil", "--repo", str(tmp_path), "ci"]):
        rc = cli.main()
    assert rc == 0
