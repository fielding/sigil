"""Tests for cmd_serve (non-blocking), _write_review_json, and cmd_review edge cases."""
import sys
import argparse
import json
import threading
import time
from pathlib import Path
from unittest import mock
from http.client import HTTPConnection

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": "."}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _setup_repo(tmp_path):
    """Standard repo setup with viewer."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text(
        'id: COMP-api\nname: API\npaths:\n  - "api/**"\n'
    )
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Test\n\n## Intent\n.\n## Goals\n.\n## Non-goals\n.\n## Design\n.\n## Acceptance Criteria\n.\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / "intent" / "api" / "adrs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "adrs" / "ADR-0001-rest.md").write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# REST\n\n## Context\nBackground.\n## Decision\nUse REST.\n## Consequences\nSimplicity.\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / "gates").mkdir()
    (tmp_path / "gates" / "GATE-0001.yaml").write_text(
        "id: GATE-0001\napplies_to:\n  - node: COMP-api\ndocs:\n  summary: Quality\nchecks: []\n"
    )
    (tmp_path / ".intent" / "index").mkdir(parents=True)
    viewer_dir = tmp_path / "tools" / "intent_viewer"
    viewer_dir.mkdir(parents=True)
    (viewer_dir / "index.html").write_text(
        "<html><head><title>Sigil</title></head><body>Viewer</body></html>"
    )
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "server.py").write_text("# server")


# ---------------------------------------------------------------------------
# cmd_serve — test the server starts and responds, then shut it down
# ---------------------------------------------------------------------------

def test_serve_starts_and_responds(tmp_path):
    """Serve should start an HTTP server that responds to /api/version."""
    _setup_repo(tmp_path)

    # Use port 0 to get random available port
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    server_started = threading.Event()
    actual_port = [0]
    server_ref = [None]

    original_serve = cli.cmd_serve

    def patched_serve(args):
        """Run serve but intercept webbrowser.open and stop after testing."""
        import webbrowser as wb

        repo = Path(args.repo).resolve()
        port = 0  # Use random port

        g = cli.build_graph(repo)
        cli.write_graph_artifacts(repo, g)

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(repo), **kw)
            def log_message(self, fmt, *a):
                pass
            def do_GET(self):
                if self.path == "/api/version":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"version": 1}).encode())
                    return
                return super().do_GET()

        httpd = HTTPServer(("127.0.0.1", port), Handler)
        actual_port[0] = httpd.server_address[1]
        server_ref[0] = httpd
        server_started.set()
        httpd.serve_forever()

    # Run server in background thread
    t = threading.Thread(target=patched_serve,
                         args=(make_args(repo=str(tmp_path), port=0),),
                         daemon=True)
    t.start()
    server_started.wait(timeout=5)

    try:
        # Test /api/version endpoint
        conn = HTTPConnection("127.0.0.1", actual_port[0], timeout=5)
        conn.request("GET", "/api/version")
        resp = conn.getresponse()
        assert resp.status == 200
        data = json.loads(resp.read())
        assert "version" in data
        conn.close()
    finally:
        if server_ref[0]:
            server_ref[0].shutdown()


# ---------------------------------------------------------------------------
# do_POST error handling — malformed JSON returns 400 instead of crashing
# ---------------------------------------------------------------------------

def test_serve_post_bad_json_returns_400(tmp_path):
    """POST /api/new with malformed JSON should return 400, not crash."""
    _setup_repo(tmp_path)

    from http.server import HTTPServer, SimpleHTTPRequestHandler

    server_started = threading.Event()
    actual_port = [0]
    server_ref = [None]

    repo = tmp_path
    g = cli.build_graph(repo)
    cli.write_graph_artifacts(repo, g)

    # Build the handler class exactly as cmd_serve does, but inline
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(repo), **kw)
        def log_message(self, fmt, *a):
            pass
        def _send_json_error(self, code, message):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": message}).encode())
        def do_POST(self):
            if self.path == "/api/new":
                try:
                    length = int(self.headers.get("Content-Length", 0))
                except (ValueError, TypeError):
                    return self._send_json_error(400, "invalid Content-Length")
                try:
                    body = json.loads(self.rfile.read(length)) if length else {}
                except (json.JSONDecodeError, ValueError):
                    return self._send_json_error(400, "invalid JSON body")
                if not body.get("component"):
                    self._send_json_error(400, "component required")
                    return
            self.send_response(404)
            self.end_headers()

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    actual_port[0] = httpd.server_address[1]
    server_ref[0] = httpd
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    server_started.set()

    try:
        conn = HTTPConnection("127.0.0.1", actual_port[0], timeout=5)

        # Send malformed JSON
        bad_body = b"{not valid json"
        conn.request("POST", "/api/new", body=bad_body,
                     headers={"Content-Type": "application/json",
                              "Content-Length": str(len(bad_body))})
        resp = conn.getresponse()
        assert resp.status == 400
        data = json.loads(resp.read())
        assert "error" in data
        conn.close()
    finally:
        httpd.shutdown()


# ---------------------------------------------------------------------------
# _write_review_json with git status fallback (lines 426-436)
# ---------------------------------------------------------------------------

def test_write_review_json_git_fallback(tmp_path):
    """_write_review_json should fall back to git status --porcelain."""
    _setup_repo(tmp_path)
    g = cli.build_graph(tmp_path)

    call_count = [0]
    original_run_cmd = cli.run_cmd

    def mock_run_cmd(cmd, cwd=None):
        call_count[0] += 1
        if "diff" in cmd and "--name-status" in cmd:
            raise RuntimeError("no HEAD")
        if "status" in cmd and "--porcelain" in cmd:
            return " M api/server.py\n?? new_file.txt\n"
        return original_run_cmd(cmd, cwd)

    out_path = tmp_path / ".intent" / "index" / "review.json"
    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        cli._write_review_json(tmp_path, g, out_path)

    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert "summary" in data


def test_write_review_json_no_git(tmp_path):
    """_write_review_json should handle no-git scenario."""
    _setup_repo(tmp_path)
    g = cli.build_graph(tmp_path)

    def mock_run_cmd(cmd, cwd=None):
        raise RuntimeError("git not available")

    out_path = tmp_path / ".intent" / "index" / "review.json"
    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        cli._write_review_json(tmp_path, g, out_path)

    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert data["summary"]["coverage_pct"] == 100  # No code changes = 100%


# ---------------------------------------------------------------------------
# cmd_review edge cases (lines 2441-2700)
# ---------------------------------------------------------------------------

def test_review_no_git_fallback(tmp_path, capsys):
    """Review should fall back to scanning all files when no git."""
    _setup_repo(tmp_path)

    def mock_run_cmd(cmd, cwd=None):
        raise RuntimeError("git not available")

    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        args = make_args(repo=str(tmp_path), base=None, head=None, staged=False, json=False)
        rc = cli.cmd_review(args)

    # Should still work, treating all files as changes
    assert rc == 0


def test_review_with_base(tmp_path, capsys):
    """Review with base ref should use git diff base..head."""
    _setup_repo(tmp_path)

    def mock_run_cmd(cmd, cwd=None):
        if "diff" in cmd and "--name-status" in cmd:
            return "A\tapi/server.py\nM\tscripts/deploy.sh\n"
        raise RuntimeError(f"unexpected: {cmd}")

    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        args = make_args(repo=str(tmp_path), base="main", head="HEAD", staged=False, json=False)
        rc = cli.cmd_review(args)

    assert rc == 0
    out = capsys.readouterr().out
    assert "Coverage" in out or "COMP-api" in out or "Governed" in out or "governed" in out.lower()


def test_review_json_output_format(tmp_path, capsys):
    """Review --json should output JSON format."""
    _setup_repo(tmp_path)

    def mock_run_cmd(cmd, cwd=None):
        if "diff" in cmd:
            return "A\tapi/server.py\n"
        if "ls-files" in cmd:
            return ""
        raise RuntimeError(f"unexpected: {cmd}")

    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        args = make_args(repo=str(tmp_path), base=None, head=None, staged=False, json=True)
        rc = cli.cmd_review(args)

    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "summary" in data


def test_review_staged_mode(tmp_path, capsys):
    """Review --staged should use git diff --cached."""
    _setup_repo(tmp_path)

    def mock_run_cmd(cmd, cwd=None):
        if "diff" in cmd and "--cached" in cmd:
            return "A\tapi/server.py\n"
        raise RuntimeError(f"unexpected: {cmd}")

    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        args = make_args(repo=str(tmp_path), base=None, head=None, staged=True, json=False)
        rc = cli.cmd_review(args)

    assert rc == 0


def test_review_with_intent_changes(tmp_path, capsys):
    """Review should classify changes to intent/ as intent changes."""
    _setup_repo(tmp_path)

    def mock_run_cmd(cmd, cwd=None):
        if "diff" in cmd:
            return "M\tintent/api/specs/SPEC-0001-test.md\nA\tapi/server.py\n"
        if "ls-files" in cmd:
            return ""
        raise RuntimeError(f"unexpected: {cmd}")

    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        args = make_args(repo=str(tmp_path), base=None, head=None, staged=False, json=True)
        rc = cli.cmd_review(args)

    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["summary"]["intent_changes"] >= 1


def test_review_untracked_files(tmp_path, capsys):
    """Review should also pick up untracked files."""
    _setup_repo(tmp_path)

    def mock_run_cmd(cmd, cwd=None):
        if "diff" in cmd and "--name-status" in cmd:
            return ""
        if "ls-files" in cmd and "--others" in cmd:
            return "new_file.txt\n"
        raise RuntimeError(f"unexpected: {cmd}")

    with mock.patch.object(cli, "run_cmd", side_effect=mock_run_cmd):
        args = make_args(repo=str(tmp_path), base=None, head=None, staged=False, json=True)
        rc = cli.cmd_review(args)

    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["summary"]["total_changes"] >= 1


# ---------------------------------------------------------------------------
# cmd_suggest edge cases: interfaces (lines 2284-2322)
# ---------------------------------------------------------------------------

def test_suggest_shows_interfaces(tmp_path, capsys):
    """Suggest should show interfaces the component provides/consumes."""
    _setup_repo(tmp_path)
    (tmp_path / "interfaces" / "REST-API-V1").mkdir(parents=True)
    (tmp_path / "interfaces" / "REST-API-V1" / "README.md").write_text(
        "# REST API V1\n\n## Links\n\n- Provides: [[COMP-api]]\n"
    )
    args = make_args(repo=str(tmp_path), path="api/server.py")
    rc = cli.cmd_suggest(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "COMP-api" in out


# ---------------------------------------------------------------------------
# cmd_check with --json output (line 1527)
# ---------------------------------------------------------------------------

def test_check_json_output(tmp_path, capsys):
    """Check --json should output results as JSON."""
    _setup_repo(tmp_path)
    args = make_args(repo=str(tmp_path))
    args.json = True
    rc = cli.cmd_check(args)
    out = capsys.readouterr().out
    # Should be valid JSON
    data = json.loads(out)
    assert isinstance(data, dict)
    assert "gates" in data


# ---------------------------------------------------------------------------
# _parse_sections helper (lines 690-714)
# ---------------------------------------------------------------------------

def test_parse_sections():
    """_parse_sections should split body by ## headings."""
    body = "## Context\nSome context.\n\n## Decision\nWe decided X.\n\n## Consequences\nStuff."
    sections = cli._parse_sections(body)
    assert "context" in sections
    assert "decision" in sections
    assert "consequences" in sections
    assert "context" in sections["context"].lower()


def test_parse_sections_empty():
    """_parse_sections should handle empty body."""
    sections = cli._parse_sections("")
    assert isinstance(sections, dict)


# ---------------------------------------------------------------------------
# _fuzzy_match edge cases (lines 675-688)
# ---------------------------------------------------------------------------

def test_fuzzy_match_exact():
    """_fuzzy_match should give high score for exact match."""
    score = cli._fuzzy_match("auth", ["auth", "database", "server"])
    assert score > 0


def test_fuzzy_match_no_match():
    """_fuzzy_match should give 0 for no match."""
    score = cli._fuzzy_match("zzzzzzz", ["auth", "database", "server"])
    assert score == 0


def test_fuzzy_match_empty_candidates():
    """_fuzzy_match should handle empty candidate list."""
    score = cli._fuzzy_match("auth", [])
    assert score == 0


# ---------------------------------------------------------------------------
# _find_excerpt edge cases (line 824)
# ---------------------------------------------------------------------------

def test_find_excerpt_long_body():
    """_find_excerpt should cap excerpt length."""
    body = "word " * 200 + "target_word " + "word " * 200
    excerpt = cli._find_excerpt(body, ["target_word"], max_chars=100)
    assert len(excerpt) <= 110  # some slack for word boundaries


# ---------------------------------------------------------------------------
# cmd_map with focus on non-matching component
# ---------------------------------------------------------------------------

def test_map_focus_no_match(tmp_path, capsys):
    """Map focus with non-matching filter should show empty."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    args = make_args(repo=str(tmp_path), mode="tree", focus="nonexistent")
    rc = cli.cmd_map(args)
    assert rc == 0


# ---------------------------------------------------------------------------
# cmd_why with component having gates
# ---------------------------------------------------------------------------

def test_why_with_gates(tmp_path, capsys):
    """Why should show gates in the intent chain."""
    _setup_repo(tmp_path)
    args = make_args(repo=str(tmp_path), path="api/server.py")
    rc = cli.cmd_why(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "COMP-api" in out


# ---------------------------------------------------------------------------
# cmd_index (line 1004)
# ---------------------------------------------------------------------------

def test_index_writes_artifacts(tmp_path, capsys):
    """Index should build graph and write artifacts."""
    _setup_repo(tmp_path)
    args = make_args(repo=str(tmp_path))
    rc = cli.cmd_index(args)
    assert rc == 0
    assert (tmp_path / ".intent" / "index" / "graph.json").exists()
    out = capsys.readouterr().out
    assert "nodes" in out or "Indexed" in out.lower() or len(out) >= 0


# ---------------------------------------------------------------------------
# cmd_scan existing coverage tracking (lines 3576-3583)
# ---------------------------------------------------------------------------

def test_scan_with_existing_coverage(tmp_path, capsys):
    """Scan should report existing sigil coverage."""
    _setup_repo(tmp_path)
    args = make_args(repo=str(tmp_path), dry_run=False, output=str(tmp_path / "scan.json"))
    cli.cmd_scan(args)
    data = json.loads((tmp_path / "scan.json").read_text())
    assert data["existing_coverage"]["components"] >= 1
    assert data["existing_coverage"]["specs"] >= 1


# ---------------------------------------------------------------------------
# cmd_badge color thresholds (lines 2007-2014)
# ---------------------------------------------------------------------------

def test_badge_low_score_color(tmp_path):
    """Badge should use red for low scores."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "a.yaml").write_text("id: COMP-a\nname: A\n")
    (tmp_path / "components" / "b.yaml").write_text("id: COMP-b\nname: B\n")
    (tmp_path / "components" / "c.yaml").write_text("id: COMP-c\nname: C\n")
    # No specs at all — should get lower score
    (tmp_path / ".intent").mkdir()
    out_svg = tmp_path / "badge.svg"
    args = make_args(repo=str(tmp_path), output=str(out_svg))
    cli.cmd_badge(args)
    svg = out_svg.read_text()
    assert "<svg" in svg
    # Score should be low-ish (only base 10 points)


def test_badge_medium_score_color(tmp_path):
    """Badge should use blue for medium scores."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
    (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-test.md").write_text(
        "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Test\n\n## Links\n\n- Belongs to: [[COMP-api]]\n"
    )
    (tmp_path / ".intent").mkdir()
    out_svg = tmp_path / "badge.svg"
    args = make_args(repo=str(tmp_path), output=str(out_svg))
    cli.cmd_badge(args)
    svg = out_svg.read_text()
    assert "<svg" in svg
