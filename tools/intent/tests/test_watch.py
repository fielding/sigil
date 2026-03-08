"""Tests for sigil check --watch mode."""
import sys
import argparse
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": ".", "json": False, "watch": False, "interval": 2.0}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _setup_repo(tmp_path):
    """Create minimal repo structure with a gate."""
    (tmp_path / "components").mkdir()
    (tmp_path / "intent" / "mycomp" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "mycomp" / "adrs").mkdir(parents=True)
    (tmp_path / "interfaces").mkdir()
    (tmp_path / "gates").mkdir()
    (tmp_path / ".intent").mkdir()

    (tmp_path / "components" / "mycomp.yaml").write_text(
        "id: COMP-mycomp\ntitle: My Component\npaths:\n  - src/**\n",
        encoding="utf-8",
    )
    (tmp_path / "intent" / "mycomp" / "specs" / "SPEC-0001-foo.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Foo\n\n## Intent\nTest.\n\n## Acceptance Criteria\n\n- Works\n\n## Links\n\n- Belongs to: [[COMP-mycomp]]\n",
        encoding="utf-8",
    )
    (tmp_path / "intent" / "mycomp" / "adrs" / "ADR-0001-bar.md").write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# Bar\n\n## Context\nTest.\n\n## Decision\nOk.\n\n## Links\n\n- For: [[SPEC-0001]]\n",
        encoding="utf-8",
    )
    (tmp_path / "gates" / "GATE-0001-spec-quality.yaml").write_text(
        "id: GATE-0001\ntype: spec-quality\nstatus: active\napplies_to:\n  - node: COMP-mycomp\nenforced_by:\n  kind: lint-rule\n  checks:\n    - all_specs_have_acceptance_criteria\n    - all_specs_have_status\npolicy:\n  on_fail: block\n",
        encoding="utf-8",
    )
    return tmp_path


# ---------------------------------------------------------------------------
# _snapshot_mtimes
# ---------------------------------------------------------------------------

def test_snapshot_mtimes_collects_intent_files(tmp_path):
    repo = _setup_repo(tmp_path)
    mtimes = cli._snapshot_mtimes(repo)
    # Should have entries for components, intent specs/adrs, gates
    paths = list(mtimes.keys())
    assert any("components" in p for p in paths)
    assert any("gates" in p for p in paths)
    assert any("intent" in p for p in paths)


def test_snapshot_mtimes_detects_change(tmp_path):
    repo = _setup_repo(tmp_path)
    before = cli._snapshot_mtimes(repo)

    # Touch a gate file
    time.sleep(0.05)
    gate_file = repo / "gates" / "GATE-0001-spec-quality.yaml"
    gate_file.write_text(gate_file.read_text() + "\n", encoding="utf-8")

    after = cli._snapshot_mtimes(repo)
    assert before != after


def test_snapshot_mtimes_detects_new_file(tmp_path):
    repo = _setup_repo(tmp_path)
    before = cli._snapshot_mtimes(repo)

    (repo / "components" / "new.yaml").write_text("id: COMP-new\ntitle: New\n", encoding="utf-8")

    after = cli._snapshot_mtimes(repo)
    assert len(after) > len(before)


def test_snapshot_mtimes_includes_config(tmp_path):
    repo = _setup_repo(tmp_path)
    cfg = repo / ".intent" / "config.yaml"
    cfg.write_text("version: 1\n", encoding="utf-8")

    mtimes = cli._snapshot_mtimes(repo)
    assert any("config.yaml" in p for p in mtimes.keys())


# ---------------------------------------------------------------------------
# _run_check_once
# ---------------------------------------------------------------------------

def test_run_check_once_returns_zero_on_pass(tmp_path):
    repo = _setup_repo(tmp_path)
    rc = cli._run_check_once(repo, use_json=False)
    assert rc == 0


def test_run_check_once_json_mode(tmp_path, capsys):
    repo = _setup_repo(tmp_path)
    rc = cli._run_check_once(repo, use_json=True)
    assert rc == 0
    import json
    output = json.loads(capsys.readouterr().out)
    assert "gates" in output
    assert output["failed"] == 0


def test_run_check_once_no_gates_dir(tmp_path, capsys):
    (tmp_path / "components").mkdir()
    (tmp_path / "intent").mkdir()
    (tmp_path / "interfaces").mkdir()
    (tmp_path / ".intent").mkdir()
    # No gates/ directory
    rc = cli._run_check_once(tmp_path, use_json=False)
    assert rc == 0
    assert "No gates/" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# cmd_check without --watch (regression)
# ---------------------------------------------------------------------------

def test_cmd_check_without_watch(tmp_path):
    repo = _setup_repo(tmp_path)
    args = make_args(repo=str(repo))
    rc = cli.cmd_check(args)
    assert rc == 0


# ---------------------------------------------------------------------------
# cmd_check --watch (integration)
# ---------------------------------------------------------------------------

def test_cmd_check_watch_detects_change(tmp_path, capsys):
    """Watch mode should detect a file change and re-run checks."""
    repo = _setup_repo(tmp_path)

    results = {"runs": 0}

    # Monkey-patch _run_check_once to count invocations and stop after 2
    original_run = cli._run_check_once

    def counting_run(r, j):
        results["runs"] += 1
        rc = original_run(r, j)
        if results["runs"] >= 2:
            raise KeyboardInterrupt()
        return rc

    cli._run_check_once = counting_run

    def modify_file():
        time.sleep(0.15)
        gate_file = repo / "gates" / "GATE-0001-spec-quality.yaml"
        gate_file.write_text(gate_file.read_text() + "\n", encoding="utf-8")

    try:
        t = threading.Thread(target=modify_file, daemon=True)
        t.start()

        args = make_args(repo=str(repo), watch=True, interval=0.1)
        rc = cli.cmd_check(args)
        t.join(timeout=2)

        assert results["runs"] >= 2
        output = capsys.readouterr().out
        assert "Change detected" in output
    finally:
        cli._run_check_once = original_run


def test_cmd_check_watch_prints_header(tmp_path, capsys):
    """Watch mode should print a header message."""
    repo = _setup_repo(tmp_path)

    original_snapshot = cli._snapshot_mtimes
    call_count = {"n": 0}

    def counting_snapshot(r):
        call_count["n"] += 1
        if call_count["n"] > 1:
            # Second call is inside the watch loop, after sleep
            raise KeyboardInterrupt()
        return original_snapshot(r)

    cli._snapshot_mtimes = counting_snapshot

    try:
        args = make_args(repo=str(repo), watch=True, interval=0.1)
        cli.cmd_check(args)
        output = capsys.readouterr().out
        assert "Watching intent files" in output
    finally:
        cli._snapshot_mtimes = original_snapshot


# ---------------------------------------------------------------------------
# cmd_watch (standalone watch command)
# ---------------------------------------------------------------------------

def test_cmd_watch_initial_summary(tmp_path, capsys):
    """Watch command prints initial summary then exits on KeyboardInterrupt."""
    repo = _setup_repo(tmp_path)
    args = make_args(repo=str(repo), interval=0.1)

    original_sleep = time.sleep

    def fake_sleep(s):
        raise KeyboardInterrupt()

    time.sleep = fake_sleep
    try:
        rc = cli.cmd_watch(args)
    finally:
        time.sleep = original_sleep

    assert rc == 0
    out = capsys.readouterr().out
    assert "Sigil Watch" in out
    assert "nodes" in out
    assert "Watch stopped" in out


def test_cmd_watch_detects_change(tmp_path, capsys):
    """Watch detects file change, re-indexes, shows changed files."""
    repo = _setup_repo(tmp_path)
    args = make_args(repo=str(repo), interval=0.1)

    original_sleep = time.sleep
    call_count = [0]
    spec = repo / "intent" / "mycomp" / "specs" / "SPEC-0001-foo.md"

    def fake_sleep(s):
        call_count[0] += 1
        if call_count[0] == 1:
            spec.write_text(spec.read_text() + "\nUpdated.\n", encoding="utf-8")
        elif call_count[0] >= 2:
            raise KeyboardInterrupt()

    time.sleep = fake_sleep
    try:
        rc = cli.cmd_watch(args)
    finally:
        time.sleep = original_sleep

    assert rc == 0
    out = capsys.readouterr().out
    assert "file(s) changed" in out
    assert "~" in out  # modified file indicator


def test_cmd_watch_json_output(tmp_path, capsys):
    """Watch --json outputs JSON summary."""
    repo = _setup_repo(tmp_path)
    args = make_args(repo=str(repo), json=True, interval=0.1)

    original_sleep = time.sleep

    def fake_sleep(s):
        raise KeyboardInterrupt()

    time.sleep = fake_sleep
    try:
        rc = cli.cmd_watch(args)
    finally:
        time.sleep = original_sleep

    assert rc == 0
    out = capsys.readouterr().out
    assert '"nodes"' in out
    assert '"edges"' in out


def test_cmd_watch_shows_added_files(tmp_path, capsys):
    """Watch shows added files with + prefix."""
    repo = _setup_repo(tmp_path)
    args = make_args(repo=str(repo), interval=0.1)

    original_sleep = time.sleep
    call_count = [0]

    def fake_sleep(s):
        call_count[0] += 1
        if call_count[0] == 1:
            (repo / "components" / "new.yaml").write_text(
                "id: COMP-new\ntitle: New\n", encoding="utf-8"
            )
        elif call_count[0] >= 2:
            raise KeyboardInterrupt()

    time.sleep = fake_sleep
    try:
        rc = cli.cmd_watch(args)
    finally:
        time.sleep = original_sleep

    assert rc == 0
    out = capsys.readouterr().out
    assert "+" in out
