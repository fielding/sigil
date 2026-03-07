"""Tests for review and hook commands."""
import sys
import argparse
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": "."}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _scaffold_repo(tmp_path):
    """Create a minimal sigil repo with git and a component."""
    # Init git
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"],
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Test"],
        capture_output=True,
    )

    # Create component with path patterns
    comp_dir = tmp_path / "components"
    comp_dir.mkdir()
    (comp_dir / "web.yaml").write_text(
        "id: COMP-web\ntitle: Web App\npaths:\n  - 'src/**'\n  - 'web/**'\n",
        encoding="utf-8",
    )

    # Create a spec for the component
    spec_dir = tmp_path / "intent" / "web" / "specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "SPEC-0001-auth.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\ntitle: Auth\ncomponent: COMP-web\n---\n\n# Auth\n\n## Intent\nAuth system.\n\n## Goals\n- Login\n\n## Non-goals\n- OAuth\n\n## Design\nBasic.\n\n## Acceptance Criteria\n- Works\n\n## Links\n\n- Belongs to: [[COMP-web]]\n",
        encoding="utf-8",
    )

    # Initial commit
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "init"],
        capture_output=True,
    )
    return tmp_path


# ---------------------------------------------------------------------------
# review
# ---------------------------------------------------------------------------


def test_review_no_changes(tmp_path):
    _scaffold_repo(tmp_path)
    args = make_args(repo=str(tmp_path), base=None, head=None, staged=False, json=False)
    rc = cli.cmd_review(args)
    assert rc == 0


def test_review_with_governed_change(tmp_path, capsys):
    _scaffold_repo(tmp_path)
    # Add a file that matches the component pattern
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "login.py").write_text("# login", encoding="utf-8")

    args = make_args(repo=str(tmp_path), base=None, head=None, staged=False, json=False)
    rc = cli.cmd_review(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "COMP-web" in out
    assert "login.py" in out


def test_review_with_ungoverned_change(tmp_path, capsys):
    _scaffold_repo(tmp_path)
    # Add a file that doesn't match any component
    (tmp_path / "random.txt").write_text("hello", encoding="utf-8")

    args = make_args(repo=str(tmp_path), base=None, head=None, staged=False, json=False)
    rc = cli.cmd_review(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Ungoverned" in out
    assert "random.txt" in out


def test_review_json_output(tmp_path, capsys):
    _scaffold_repo(tmp_path)
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("# app", encoding="utf-8")

    args = make_args(repo=str(tmp_path), base=None, head=None, staged=False, json=True)
    rc = cli.cmd_review(args)
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "summary" in data
    assert data["summary"]["covered_files"] >= 1


def test_review_staged(tmp_path, capsys):
    _scaffold_repo(tmp_path)
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "staged.py").write_text("# staged", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "src/staged.py"], capture_output=True)

    args = make_args(repo=str(tmp_path), base=None, head=None, staged=True, json=False)
    rc = cli.cmd_review(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "staged.py" in out


# ---------------------------------------------------------------------------
# hook
# ---------------------------------------------------------------------------


def test_hook_install_and_uninstall(tmp_path):
    _scaffold_repo(tmp_path)
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"

    # Install
    args = make_args(repo=str(tmp_path), action="install")
    rc = cli.cmd_hook(args)
    assert rc == 0
    assert hook_path.exists()
    assert "Sigil" in hook_path.read_text()

    # Status should show installed
    args = make_args(repo=str(tmp_path), action="status")
    rc = cli.cmd_hook(args)
    assert rc == 0

    # Uninstall
    args = make_args(repo=str(tmp_path), action="uninstall")
    rc = cli.cmd_hook(args)
    assert rc == 0
    assert not hook_path.exists()


def test_hook_install_idempotent(tmp_path):
    _scaffold_repo(tmp_path)
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"

    args = make_args(repo=str(tmp_path), action="install")
    cli.cmd_hook(args)
    cli.cmd_hook(args)  # Second install should be a no-op

    content = hook_path.read_text()
    assert content.count("Sigil intent coverage check") == 1


def test_hook_append_to_existing(tmp_path):
    _scaffold_repo(tmp_path)
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text("#!/bin/sh\necho 'existing hook'\n", encoding="utf-8")

    args = make_args(repo=str(tmp_path), action="install")
    rc = cli.cmd_hook(args)
    assert rc == 0

    content = hook_path.read_text()
    assert "existing hook" in content
    assert "Sigil" in content
