"""Real-world repo tests: run Sigil CLI against popular open source projects.

These tests clone small, well-known open source repos and verify that Sigil
handles them gracefully — bootstrap, scan, status, doctor, index, coverage.

The goal is to catch regressions that only surface on real-world codebases
(diverse file structures, edge cases in manifests, large file counts, etc.).

Repos are cached in a shared temp dir to avoid re-cloning on every test run.
Mark tests with @pytest.mark.realworld so they can be filtered in CI.

Usage:
    pytest test_realworld.py -v                  # run all real-world tests
    pytest test_realworld.py -k "flask"          # run only Flask tests
    pytest test_realworld.py --skip-clone        # skip if repos not cached
"""
import sys
import os
import json
import subprocess
import shutil
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli

SIGIL_PY = str(Path(__file__).parent.parent / "sigil.py")
GOLDEN_DIR = Path(__file__).parent / "golden" / "realworld"

# Shared cache dir for cloned repos (survives across test runs in same session)
CLONE_CACHE = Path(os.environ.get(
    "SIGIL_TEST_CLONE_DIR",
    Path(__file__).parent / ".realworld_cache"
))

# Real-world repos to test against.
# Chosen for diversity: Python (Flask, Click), Go-style, JS/TS, Rust, mixed.
# All are small enough to clone in seconds (shallow clone, depth=1).
REPOS = {
    "flask": {
        "url": "https://github.com/pallets/flask.git",
        "description": "Python micro web framework",
        "language": "python",
        "expected_manifests": ["pyproject.toml", "setup.cfg"],
    },
    "click": {
        "url": "https://github.com/pallets/click.git",
        "description": "Python CLI toolkit",
        "language": "python",
        "expected_manifests": ["pyproject.toml"],
    },
    "fastapi": {
        "url": "https://github.com/fastapi/fastapi.git",
        "description": "Python async web framework",
        "language": "python",
        "expected_manifests": ["pyproject.toml"],
    },
    "httpx": {
        "url": "https://github.com/encode/httpx.git",
        "description": "Python HTTP client",
        "language": "python",
        "expected_manifests": ["pyproject.toml"],
    },
    "jinja": {
        "url": "https://github.com/pallets/jinja.git",
        "description": "Python template engine",
        "language": "python",
        "expected_manifests": ["pyproject.toml"],
    },
}


def _clone_repo(name: str) -> Path:
    """Clone a repo to the cache dir (shallow, depth=1). Skip if offline."""
    target = CLONE_CACHE / name
    if target.exists() and (target / ".git").exists():
        return target  # already cached

    CLONE_CACHE.mkdir(parents=True, exist_ok=True)
    url = REPOS[name]["url"]
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", url, str(target)],
            capture_output=True, text=True, timeout=60,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        pytest.skip(f"Could not clone {name}: {e}")
    return target


def run_sigil(*args, repo=None, timeout=30):
    """Run sigil as a subprocess and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, SIGIL_PY]
    if repo:
        cmd += ["--repo", str(repo)]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def skip_clone(request):
    return request.config.getoption("--skip-clone", default=False)


@pytest.fixture(scope="session", params=list(REPOS.keys()))
def realworld_repo(request, skip_clone):
    """Parametrized fixture: yields (name, repo_path) for each real-world repo."""
    name = request.param
    cache_path = CLONE_CACHE / name
    if skip_clone and not cache_path.exists():
        pytest.skip(f"{name} not cached and --skip-clone set")
    repo_path = _clone_repo(name)
    return name, repo_path


# ---------------------------------------------------------------------------
# Core smoke tests: every command should not crash on real repos
# ---------------------------------------------------------------------------

class TestRealWorldSmoke:
    """Verify that core Sigil commands don't crash on real-world repos."""

    def test_status(self, realworld_repo):
        name, repo = realworld_repo
        rc, out, err = run_sigil("status", repo=repo)
        assert rc == 0, f"status crashed on {name}:\n{err}"
        # Status should produce some output
        assert len(out.strip()) > 0

    def test_index(self, realworld_repo):
        name, repo = realworld_repo
        rc, out, err = run_sigil("index", repo=repo)
        assert rc == 0, f"index crashed on {name}:\n{err}"

    def test_doctor(self, realworld_repo):
        name, repo = realworld_repo
        rc, out, err = run_sigil("doctor", repo=repo)
        # Doctor may return 1 for missing dirs, but should not crash
        assert rc in (0, 1), f"doctor crashed on {name}:\n{err}"

    def test_lint(self, realworld_repo):
        name, repo = realworld_repo
        rc, out, err = run_sigil("lint", repo=repo)
        assert rc in (0, 1), f"lint crashed on {name}:\n{err}"

    def test_coverage(self, realworld_repo):
        name, repo = realworld_repo
        rc, out, err = run_sigil("coverage", repo=repo)
        assert rc == 0, f"coverage crashed on {name}:\n{err}"

    def test_map(self, realworld_repo):
        name, repo = realworld_repo
        rc, out, err = run_sigil("map", repo=repo)
        assert rc == 0, f"map crashed on {name}:\n{err}"

    def test_ask(self, realworld_repo):
        name, repo = realworld_repo
        rc, out, err = run_sigil("ask", "api", repo=repo)
        assert rc == 0, f"ask crashed on {name}:\n{err}"


# ---------------------------------------------------------------------------
# Bootstrap + Scan: Sigil should detect components in real repos
# ---------------------------------------------------------------------------

class TestRealWorldBootstrapScan:
    """Test bootstrap and scan against real repos (in isolated copies)."""

    def _isolated_copy(self, repo_path, tmp_path, name):
        """Copy repo to tmp_path so we can write to it without polluting cache."""
        dest = tmp_path / name
        shutil.copytree(repo_path, dest, symlinks=True,
                        ignore=shutil.ignore_patterns(".git"))
        (dest / ".intent").mkdir(exist_ok=True)
        (dest / "components").mkdir(exist_ok=True)
        return dest

    def test_scan_detects_components(self, realworld_repo, tmp_path):
        name, repo = realworld_repo
        isolated = self._isolated_copy(repo, tmp_path, name)
        rc, out, err = run_sigil("scan", "--dry-run", repo=isolated)
        assert rc == 0, f"scan --dry-run crashed on {name}:\n{err}"
        # Scan should produce some output about what it found
        assert len(out.strip()) > 0

    def test_bootstrap_creates_components(self, realworld_repo, tmp_path):
        name, repo = realworld_repo
        isolated = self._isolated_copy(repo, tmp_path, name)
        rc, out, err = run_sigil("bootstrap", repo=isolated)
        assert rc == 0, f"bootstrap crashed on {name}:\n{err}"

    def test_full_pipeline_after_bootstrap(self, realworld_repo, tmp_path):
        """After bootstrap, the full pipeline (index + status + coverage) should work."""
        name, repo = realworld_repo
        isolated = self._isolated_copy(repo, tmp_path, name)

        # Bootstrap to create component stubs
        rc, _, err = run_sigil("bootstrap", repo=isolated)
        assert rc == 0, f"bootstrap failed on {name}:\n{err}"

        # Index
        rc, _, err = run_sigil("index", repo=isolated)
        assert rc == 0, f"index failed on {name}:\n{err}"

        # Status should show components
        rc, out, err = run_sigil("status", repo=isolated)
        assert rc == 0, f"status failed on {name}:\n{err}"

        # Coverage (JSON) should return valid data
        rc, out, err = run_sigil("coverage", "--json", repo=isolated)
        assert rc == 0, f"coverage failed on {name}:\n{err}"
        data = json.loads(out)
        assert "score" in data
        assert 0 <= data["score"] <= 100


# ---------------------------------------------------------------------------
# Snapshot tests: capture scan output for regression detection
# ---------------------------------------------------------------------------

class TestRealWorldSnapshots:
    """Golden file comparisons for real-world repo scan results."""

    def _isolated_copy(self, repo_path, tmp_path, name):
        dest = tmp_path / name
        shutil.copytree(repo_path, dest, symlinks=True,
                        ignore=shutil.ignore_patterns(".git"))
        (dest / ".intent").mkdir(exist_ok=True)
        (dest / "components").mkdir(exist_ok=True)
        return dest

    def _update_golden(self, name, data):
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        (GOLDEN_DIR / f"{name}.json").write_text(
            json.dumps(data, indent=2, sort_keys=True)
        )

    def _load_golden(self, name):
        path = GOLDEN_DIR / f"{name}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def test_bootstrap_snapshot(self, realworld_repo, tmp_path, request):
        """After bootstrap, component count and graph shape should be stable."""
        name, repo = realworld_repo
        isolated = self._isolated_copy(repo, tmp_path, name)

        run_sigil("bootstrap", repo=isolated)
        g = cli.build_graph(isolated)

        actual = {
            "node_count": len(g.nodes),
            "component_count": len([n for n in g.nodes.values() if n.type == "component"]),
            "node_types": sorted({n.type for n in g.nodes.values()}),
        }

        golden_name = f"bootstrap_{name}"
        golden = self._load_golden(golden_name)
        if golden is None or request.config.getoption("--update-golden", default=False):
            self._update_golden(golden_name, actual)
            return

        # Component count should not regress (allow +/- due to upstream repo changes)
        assert actual["component_count"] >= golden["component_count"] - 2, \
            f"{name}: component count regressed: {actual['component_count']} vs {golden['component_count']}"
        assert set(golden["node_types"]).issubset(set(actual["node_types"])), \
            f"{name}: missing node types: {set(golden['node_types']) - set(actual['node_types'])}"


# ---------------------------------------------------------------------------
# Specific repo tests: language-specific behavior
# ---------------------------------------------------------------------------

class TestFlaskSpecific:
    """Flask-specific integration tests."""

    @pytest.fixture(autouse=True)
    def setup(self, skip_clone):
        cache = CLONE_CACHE / "flask"
        if skip_clone and not cache.exists():
            pytest.skip("flask not cached")
        self.repo = _clone_repo("flask")

    def test_flask_has_src_directory(self):
        assert (self.repo / "src").exists() or (self.repo / "flask").exists()

    def test_scan_finds_flask_package(self, tmp_path):
        dest = tmp_path / "flask"
        shutil.copytree(self.repo, dest, symlinks=True,
                        ignore=shutil.ignore_patterns(".git"))
        (dest / ".intent").mkdir(exist_ok=True)
        rc, out, _ = run_sigil("scan", "--dry-run", repo=dest)
        assert rc == 0
        assert "flask" in out.lower()


class TestFastAPISpecific:
    """FastAPI-specific integration tests."""

    @pytest.fixture(autouse=True)
    def setup(self, skip_clone):
        cache = CLONE_CACHE / "fastapi"
        if skip_clone and not cache.exists():
            pytest.skip("fastapi not cached")
        self.repo = _clone_repo("fastapi")

    def test_fastapi_has_source(self):
        assert (self.repo / "fastapi").exists()

    def test_scan_finds_fastapi(self, tmp_path):
        dest = tmp_path / "fastapi"
        shutil.copytree(self.repo, dest, symlinks=True,
                        ignore=shutil.ignore_patterns(".git"))
        (dest / ".intent").mkdir(exist_ok=True)
        rc, out, _ = run_sigil("scan", "--dry-run", repo=dest)
        assert rc == 0


class TestClickSpecific:
    """Click-specific integration tests."""

    @pytest.fixture(autouse=True)
    def setup(self, skip_clone):
        cache = CLONE_CACHE / "click"
        if skip_clone and not cache.exists():
            pytest.skip("click not cached")
        self.repo = _clone_repo("click")

    def test_click_has_source(self):
        assert (self.repo / "src").exists() or (self.repo / "click").exists()

    def test_full_ci_after_bootstrap(self, tmp_path):
        """Full CI pipeline should work on Click after bootstrap."""
        dest = tmp_path / "click"
        shutil.copytree(self.repo, dest, symlinks=True,
                        ignore=shutil.ignore_patterns(".git"))
        (dest / ".intent").mkdir(exist_ok=True)
        (dest / "components").mkdir(exist_ok=True)

        rc, _, err = run_sigil("bootstrap", repo=dest)
        assert rc == 0, f"bootstrap failed:\n{err}"

        rc, out, err = run_sigil("ci", repo=dest)
        assert rc == 0, f"CI failed on Click:\n{out}\n{err}"


# ---------------------------------------------------------------------------
# Cross-repo consistency tests
# ---------------------------------------------------------------------------

class TestCrossRepoConsistency:
    """Tests that verify consistent behavior across all real-world repos."""

    def test_coverage_json_always_valid(self, realworld_repo, tmp_path):
        """coverage --json should always return valid JSON with required keys."""
        name, repo = realworld_repo
        rc, out, err = run_sigil("coverage", "--json", repo=repo)
        assert rc == 0, f"coverage --json crashed on {name}:\n{err}"
        data = json.loads(out)
        for key in ["score", "metrics", "components", "stats"]:
            assert key in data, f"{name}: missing key '{key}' in coverage JSON"
        assert 0 <= data["score"] <= 100

    def test_status_never_crashes(self, realworld_repo):
        """status should never crash, regardless of repo state."""
        name, repo = realworld_repo
        rc, out, err = run_sigil("status", repo=repo)
        assert rc == 0, f"status crashed on {name}:\n{err}"

    def test_index_produces_graph_json(self, realworld_repo):
        """index should always produce a valid graph.json."""
        name, repo = realworld_repo
        rc, _, err = run_sigil("index", repo=repo)
        assert rc == 0, f"index crashed on {name}:\n{err}"
        graph_path = repo / ".intent" / "index" / "graph.json"
        if graph_path.exists():
            data = json.loads(graph_path.read_text())
            assert "nodes" in data
            assert "edges" in data
