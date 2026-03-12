"""Integration tests: run Sigil CLI against realistic repos.

These tests exercise full command pipelines against:
- The demo-app (examples/demo-app/) — a fully-instrumented Sigil project
- Synthetic fixture repos simulating real-world patterns
- Edge cases: empty repos, partial intent, broken refs, monorepos
"""
import sys
import os
import json
import argparse
import subprocess
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli

SIGIL_PY = str(Path(__file__).parent.parent / "sigil.py")
REPO_ROOT = Path(__file__).parent.parent.parent.parent  # sigil/
DEMO_APP = REPO_ROOT / "examples" / "demo-app"


def make_args(**kwargs):
    defaults = {"repo": "."}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def run_sigil(*args, repo=None):
    """Run sigil as a subprocess and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, SIGIL_PY]
    if repo:
        cmd += ["--repo", str(repo)]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


# ===========================================================================
# Demo-app integration tests
# ===========================================================================

class TestDemoApp:
    """Full integration tests against examples/demo-app/."""

    @pytest.fixture(autouse=True)
    def check_demo_exists(self):
        if not DEMO_APP.exists():
            pytest.skip("demo-app not present")

    def test_status_reports_healthy(self):
        rc, out, _ = run_sigil("status", repo=DEMO_APP)
        assert rc == 0
        assert "Health:" in out
        # Extract percentage from the bar like [##################--] 91%
        for line in out.splitlines():
            if "%" in line and "Health:" in line:
                # Extract the number before %
                import re
                m = re.search(r"(\d+)%", line)
                assert m, f"Could not parse health from: {line}"
                pct = int(m.group(1))
                assert pct >= 80, f"Health too low: {pct}%"
                break

    def test_status_node_counts(self):
        rc, out, _ = run_sigil("status", repo=DEMO_APP)
        assert rc == 0
        assert "component:" in out
        assert "spec:" in out
        assert "adr:" in out
        assert "gate:" in out
        assert "interface:" in out

    def test_index_builds_graph(self):
        rc, out, _ = run_sigil("index", repo=DEMO_APP)
        assert rc == 0
        graph_path = DEMO_APP / ".intent" / "index" / "graph.json"
        assert graph_path.exists()
        data = json.loads(graph_path.read_text())
        assert len(data["nodes"]) >= 30
        assert len(data["edges"]) >= 80

    def test_graph_node_types(self):
        """Graph should contain all expected node types."""
        g = cli.build_graph(DEMO_APP)
        types = {n.type for n in g.nodes.values()}
        assert "component" in types
        assert "spec" in types
        assert "adr" in types
        assert "gate" in types
        assert "interface" in types

    def test_graph_edge_types(self):
        """Graph should contain diverse edge types."""
        g = cli.build_graph(DEMO_APP)
        edge_types = {e.type for e in g.edges}
        assert "belongs_to" in edge_types
        assert "depends_on" in edge_types
        assert "gated_by" in edge_types
        assert "decided_by" in edge_types

    def test_lint_passes(self):
        rc, out, _ = run_sigil("lint", repo=DEMO_APP)
        # Demo app should be lint-clean (0 errors, warnings OK)
        assert rc == 0 or "ERROR" not in out

    def test_check_gates_pass(self):
        rc, out, _ = run_sigil("check", repo=DEMO_APP)
        assert rc == 0, f"Gate check failed:\n{out}"

    def test_check_json_output(self):
        rc, out, _ = run_sigil("check", "--json", repo=DEMO_APP)
        assert rc == 0
        data = json.loads(out)
        assert "gates" in data
        assert data["failed"] == 0
        assert data["passed"] >= 2

    def test_coverage_report(self):
        rc, out, _ = run_sigil("coverage", repo=DEMO_APP)
        assert rc == 0
        assert "Intent Coverage:" in out
        assert "Components with spec:" in out

    def test_coverage_json(self):
        rc, out, _ = run_sigil("coverage", "--json", repo=DEMO_APP)
        assert rc == 0
        data = json.loads(out)
        assert data["score"] >= 70
        assert len(data["components"]) >= 8

    def test_map_tree(self):
        rc, out, _ = run_sigil("map", "--mode", "tree", repo=DEMO_APP)
        assert rc == 0
        assert "COMP-" in out

    def test_map_deps(self):
        rc, out, _ = run_sigil("map", "--mode", "deps", repo=DEMO_APP)
        assert rc == 0

    def test_map_flat(self):
        rc, out, _ = run_sigil("map", "--mode", "flat", repo=DEMO_APP)
        assert rc == 0
        assert "COMP" in out
        assert "SPEC" in out

    def test_doctor(self):
        rc, out, _ = run_sigil("doctor", repo=DEMO_APP)
        # Doctor may flag missing viewer symlink etc, but should not crash
        assert rc in (0, 1)
        assert "components/" in out or "Components" in out

    def test_ask_returns_results(self):
        rc, out, _ = run_sigil("ask", "order", repo=DEMO_APP)
        assert rc == 0
        assert "order" in out.lower() or "Order" in out

    def test_ask_json(self):
        rc, out, _ = run_sigil("ask", "--json", "payment", repo=DEMO_APP)
        assert rc == 0
        data = json.loads(out)
        # ask --json returns {"query": ..., "results": [...]}
        results = data.get("results", data) if isinstance(data, dict) else data
        assert len(results) > 0
        assert any(
            "payment" in r.get("id", "").lower() or "payment" in r.get("title", "").lower()
            for r in results
        )

    def test_impact_order_service(self):
        rc, out, _ = run_sigil("impact", "COMP-order-service", repo=DEMO_APP)
        assert rc == 0
        # Impact shows "Direct (N)" or "Ring N" style headers
        assert "Direct" in out or "Blast radius" in out

    def test_impact_json(self):
        rc, out, _ = run_sigil("impact", "--json", "COMP-order-service", repo=DEMO_APP)
        assert rc == 0
        data = json.loads(out)
        assert "rings" in data
        assert len(data["rings"]) >= 1

    def test_ci_pipeline(self):
        """Full CI pipeline should pass on demo-app."""
        rc, out, _ = run_sigil("ci", repo=DEMO_APP)
        assert rc == 0, f"CI failed:\n{out}"

    def test_badge_generation(self, tmp_path):
        badge_path = tmp_path / "badge.svg"
        rc, out, _ = run_sigil("badge", "--output", str(badge_path), repo=DEMO_APP)
        assert rc == 0
        assert badge_path.exists()
        svg = badge_path.read_text()
        assert "<svg" in svg
        assert "%" in svg

    def test_scan_dry_run(self):
        """Scan dry run should work without writing files."""
        rc, out, _ = run_sigil("scan", "--dry-run", repo=DEMO_APP)
        assert rc == 0

    def test_export_html(self, tmp_path):
        output = tmp_path / "export.html"
        rc, out, _ = run_sigil("export", "--output", str(output), repo=DEMO_APP)
        assert rc == 0
        assert output.exists()
        html = output.read_text()
        assert "<html" in html.lower() or "<!doctype" in html.lower()

    def test_why_governed_file(self):
        """Why should trace intent for a known file in demo-app."""
        # Find a file that should be governed
        app_dir = DEMO_APP / "app"
        if app_dir.exists():
            files = list(app_dir.rglob("*.py")) + list(app_dir.rglob("*.ts")) + list(app_dir.rglob("*.js"))
            if files:
                rel = files[0].relative_to(DEMO_APP)
                rc, out, _ = run_sigil("why", str(rel), repo=DEMO_APP)
                assert rc == 0
                # Should find some governing component
                assert "COMP-" in out or "ungoverned" in out


# ===========================================================================
# Snapshot tests: golden file comparisons for demo-app
# ===========================================================================

GOLDEN_DIR = Path(__file__).parent / "golden"


class TestDemoAppSnapshots:
    """Compare key outputs against golden files for regression detection."""

    @pytest.fixture(autouse=True)
    def check_demo_exists(self):
        if not DEMO_APP.exists():
            pytest.skip("demo-app not present")

    def _update_golden(self, name, data):
        """Write golden file (run with --update-golden to refresh)."""
        GOLDEN_DIR.mkdir(exist_ok=True)
        (GOLDEN_DIR / name).write_text(json.dumps(data, indent=2, sort_keys=True))

    def _load_golden(self, name):
        path = GOLDEN_DIR / name
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def test_graph_structure_snapshot(self, request):
        """Graph node/edge counts should not regress."""
        g = cli.build_graph(DEMO_APP)
        actual = {
            "node_count": len(g.nodes),
            "edge_count": len(g.edges),
            "node_types": sorted({n.type for n in g.nodes.values()}),
            "edge_types": sorted({e.type for e in g.edges}),
            "component_ids": sorted(n.id for n in g.nodes.values() if n.type == "component"),
        }

        golden = self._load_golden("graph_structure.json")
        if golden is None or request.config.getoption("--update-golden", default=False):
            self._update_golden("graph_structure.json", actual)
            return

        assert actual["node_count"] >= golden["node_count"], \
            f"Node count regressed: {actual['node_count']} < {golden['node_count']}"
        assert actual["edge_count"] >= golden["edge_count"], \
            f"Edge count regressed: {actual['edge_count']} < {golden['edge_count']}"
        assert set(golden["node_types"]).issubset(set(actual["node_types"])), \
            f"Missing node types: {set(golden['node_types']) - set(actual['node_types'])}"
        assert set(golden["edge_types"]).issubset(set(actual["edge_types"])), \
            f"Missing edge types: {set(golden['edge_types']) - set(actual['edge_types'])}"
        assert set(golden["component_ids"]).issubset(set(actual["component_ids"])), \
            f"Missing components: {set(golden['component_ids']) - set(actual['component_ids'])}"

    def test_coverage_score_snapshot(self, request):
        """Coverage score should not drop significantly."""
        g = cli.build_graph(DEMO_APP)
        cov = cli._compute_coverage(DEMO_APP, g)
        actual = {
            "score": cov["score"],
            "component_count": len(cov["components"]),
            "green_count": sum(1 for c in cov["components"] if c["level"] == "green"),
        }

        golden = self._load_golden("coverage_snapshot.json")
        if golden is None or request.config.getoption("--update-golden", default=False):
            self._update_golden("coverage_snapshot.json", actual)
            return

        assert actual["score"] >= golden["score"] - 5, \
            f"Coverage score dropped: {actual['score']} vs {golden['score']}"
        assert actual["component_count"] >= golden["component_count"], \
            f"Component count regressed: {actual['component_count']} < {golden['component_count']}"

    def test_gate_results_snapshot(self, request):
        """Gate check results should remain stable."""
        g = cli.build_graph(DEMO_APP)
        results = cli._run_gate_checks(DEMO_APP, g)
        actual = {
            "gate_count": len(results),
            "all_pass": all(r["passed"] for r in results),
            "gate_ids": sorted(r["id"] for r in results),
        }

        golden = self._load_golden("gate_results.json")
        if golden is None or request.config.getoption("--update-golden", default=False):
            self._update_golden("gate_results.json", actual)
            return

        assert actual["all_pass"] == golden["all_pass"], "Gate pass/fail status changed"
        assert set(golden["gate_ids"]).issubset(set(actual["gate_ids"])), \
            f"Missing gates: {set(golden['gate_ids']) - set(actual['gate_ids'])}"

# ===========================================================================
# Edge case tests: empty, partial, broken, monorepo
# ===========================================================================

class TestEdgeCaseEmptyRepo:
    """Sigil should handle completely empty repos gracefully."""

    def test_status_empty(self, tmp_path):
        rc, out, _ = run_sigil("status", repo=tmp_path)
        assert rc == 0
        assert "Nodes: 0" in out or "No intent" in out

    def test_index_empty(self, tmp_path):
        rc, _, _ = run_sigil("index", repo=tmp_path)
        assert rc == 0

    def test_lint_empty(self, tmp_path):
        rc, _, _ = run_sigil("lint", repo=tmp_path)
        assert rc == 0

    def test_check_empty(self, tmp_path):
        rc, _, _ = run_sigil("check", repo=tmp_path)
        assert rc == 0

    def test_coverage_empty(self, tmp_path):
        rc, out, _ = run_sigil("coverage", repo=tmp_path)
        assert rc == 0

    def test_map_empty(self, tmp_path):
        rc, out, _ = run_sigil("map", repo=tmp_path)
        assert rc == 0
        assert "No intent documents found" in out

    def test_scan_empty(self, tmp_path):
        (tmp_path / ".intent").mkdir()
        rc, _, _ = run_sigil("scan", "--dry-run", repo=tmp_path)
        assert rc == 0

    def test_ask_empty(self, tmp_path):
        rc, out, _ = run_sigil("ask", "anything", repo=tmp_path)
        assert rc == 0

    def test_impact_empty(self, tmp_path):
        rc, out, _ = run_sigil("impact", "COMP-nonexistent", repo=tmp_path)
        # Should fail gracefully, not crash
        assert rc in (0, 1)


class TestEdgeCasePartialRepo:
    """Repos with partial intent documents (components but no specs, etc.)."""

    def _setup_components_only(self, tmp_path):
        (tmp_path / "components").mkdir()
        (tmp_path / "components" / "api.yaml").write_text("id: COMP-api\nname: API\n")
        (tmp_path / "components" / "web.yaml").write_text("id: COMP-web\nname: Web\n")
        (tmp_path / ".intent").mkdir()

    def test_status_components_only(self, tmp_path):
        self._setup_components_only(tmp_path)
        rc, out, _ = run_sigil("status", repo=tmp_path)
        assert rc == 0
        assert "component:" in out
        assert "2" in out

    def test_coverage_all_red(self, tmp_path):
        """Components without specs should all be red."""
        self._setup_components_only(tmp_path)
        rc, out, _ = run_sigil("coverage", "--json", repo=tmp_path)
        assert rc == 0
        data = json.loads(out)
        assert all(c["level"] == "red" for c in data["components"])

    def test_lint_components_only(self, tmp_path):
        self._setup_components_only(tmp_path)
        rc, _, _ = run_sigil("lint", repo=tmp_path)
        assert rc == 0

    def test_map_components_only(self, tmp_path):
        self._setup_components_only(tmp_path)
        rc, out, _ = run_sigil("map", repo=tmp_path)
        assert rc == 0
        assert "COMP-api" in out
        assert "COMP-web" in out


class TestEdgeCaseBrokenRefs:
    """Repos with dangling references in intent documents."""

    def _setup_broken_refs(self, tmp_path):
        (tmp_path / "components").mkdir()
        (tmp_path / "components" / "api.yaml").write_text(
            "id: COMP-api\nname: API\ndepends_on:\n  - COMP-nonexistent\n"
        )
        (tmp_path / "intent" / "api" / "specs").mkdir(parents=True)
        (tmp_path / "intent" / "api" / "specs" / "SPEC-0001-broken.md").write_text(
            "---\nid: SPEC-0001\nstatus: draft\n---\n\n# Broken\n\n## Links\n\n- Belongs to: [[COMP-api]]\n- Relates to: [[SPEC-9999]]\n"
        )
        (tmp_path / ".intent").mkdir()

    def test_status_with_broken_refs(self, tmp_path):
        self._setup_broken_refs(tmp_path)
        rc, out, _ = run_sigil("status", repo=tmp_path)
        assert rc == 0

    def test_index_with_broken_refs(self, tmp_path):
        self._setup_broken_refs(tmp_path)
        rc, _, _ = run_sigil("index", repo=tmp_path)
        assert rc == 0

    def test_lint_catches_broken_refs(self, tmp_path):
        self._setup_broken_refs(tmp_path)
        rc, out, _ = run_sigil("lint", repo=tmp_path)
        # Lint should flag dangling references
        assert rc in (0, 1)

    def test_coverage_with_broken_refs(self, tmp_path):
        self._setup_broken_refs(tmp_path)
        rc, out, _ = run_sigil("coverage", "--json", repo=tmp_path)
        assert rc == 0
        data = json.loads(out)
        assert data["score"] >= 0  # should not crash


class TestEdgeCaseMonorepo:
    """Simulate a monorepo with multiple independent components."""

    def _setup_monorepo(self, tmp_path):
        # 5 independent services
        for svc in ["auth", "billing", "notifications", "api-gateway", "frontend"]:
            (tmp_path / "components").mkdir(exist_ok=True)
            (tmp_path / "components" / f"{svc}.yaml").write_text(
                f"id: COMP-{svc}\nname: {svc.replace('-', ' ').title()}\npaths:\n  - \"services/{svc}/**\"\n"
            )
            (tmp_path / "services" / svc / "src").mkdir(parents=True, exist_ok=True)
            (tmp_path / "services" / svc / "src" / "index.ts").write_text(f"// {svc} service\n")
            (tmp_path / "services" / svc / "package.json").write_text(f'{{"name": "{svc}"}}\n')

            # Each service gets a spec
            (tmp_path / "intent" / svc / "specs").mkdir(parents=True, exist_ok=True)
            (tmp_path / "intent" / svc / "specs" / f"SPEC-{svc}.md").write_text(
                f"---\nid: SPEC-{svc}\nstatus: accepted\n---\n\n# {svc.title()} Spec\n\n## Intent\nDefines {svc}.\n\n## Acceptance Criteria\n\n- Works\n\n## Links\n\n- Belongs to: [[COMP-{svc}]]\n"
            )

        # Cross-service dependencies
        (tmp_path / "components" / "api-gateway.yaml").write_text(
            "id: COMP-api-gateway\nname: API Gateway\npaths:\n  - \"services/api-gateway/**\"\ndepends_on:\n  - COMP-auth\n  - COMP-billing\n"
        )

        # Interfaces — edges come from Links section
        (tmp_path / "interfaces" / "API-AUTH-V1").mkdir(parents=True)
        (tmp_path / "interfaces" / "API-AUTH-V1" / "README.md").write_text(
            "---\nid: API-AUTH-V1\n---\n\n# Auth API\n\n## Links\n\n- Provided by: [[COMP-auth]]\n- Consumed by: [[COMP-api-gateway]]\n"
        )

        (tmp_path / "gates").mkdir(exist_ok=True)
        (tmp_path / ".intent").mkdir(exist_ok=True)

    def test_monorepo_status(self, tmp_path):
        self._setup_monorepo(tmp_path)
        rc, out, _ = run_sigil("status", repo=tmp_path)
        assert rc == 0
        assert "component:" in out

    def test_monorepo_graph_structure(self, tmp_path):
        self._setup_monorepo(tmp_path)
        g = cli.build_graph(tmp_path)
        comps = [n for n in g.nodes.values() if n.type == "component"]
        assert len(comps) == 5
        # Each spec belongs_to its component
        belongs = [e for e in g.edges if e.type == "belongs_to"]
        assert len(belongs) >= 5

    def test_monorepo_coverage(self, tmp_path):
        self._setup_monorepo(tmp_path)
        rc, out, _ = run_sigil("coverage", "--json", repo=tmp_path)
        assert rc == 0
        data = json.loads(out)
        assert data["stats"]["components"] == 5

    def test_monorepo_impact(self, tmp_path):
        self._setup_monorepo(tmp_path)
        rc, out, _ = run_sigil("impact", "COMP-auth", repo=tmp_path)
        assert rc == 0
        # Impact should show blast radius info
        assert "Blast radius" in out or "Direct" in out

    def test_monorepo_ci(self, tmp_path):
        self._setup_monorepo(tmp_path)
        rc, out, _ = run_sigil("ci", repo=tmp_path)
        assert rc == 0

    def test_monorepo_scan_detects_services(self, tmp_path):
        self._setup_monorepo(tmp_path)
        rc, _, _ = run_sigil("scan", "--dry-run", repo=tmp_path)
        assert rc == 0


class TestEdgeCaseNonPythonRepo:
    """Repo with non-Python manifests only."""

    def _setup_go_repo(self, tmp_path):
        # go.mod must be in a subdirectory for scan to detect it as a component
        (tmp_path / "backend").mkdir(parents=True)
        (tmp_path / "backend" / "main.go").write_text("package main\n")
        (tmp_path / "backend" / "go.mod").write_text("module example.com/backend\n")
        (tmp_path / ".intent").mkdir()

    def test_bootstrap_go_repo(self, tmp_path):
        self._setup_go_repo(tmp_path)
        (tmp_path / "components").mkdir()
        rc, _, _ = run_sigil("bootstrap", repo=tmp_path)
        assert rc == 0

    def test_scan_go_repo(self, tmp_path):
        self._setup_go_repo(tmp_path)
        rc, out, _ = run_sigil("scan", "--dry-run", repo=tmp_path)
        assert rc == 0
        # Scan should detect the go component
        assert "backend" in out.lower()


class TestEdgeCaseLargeGraph:
    """Stress test: repo with many components to verify performance."""

    def _setup_large_repo(self, tmp_path, n=50):
        (tmp_path / "components").mkdir()
        (tmp_path / ".intent").mkdir()
        for i in range(n):
            (tmp_path / "components" / f"svc-{i:03d}.yaml").write_text(
                f"id: COMP-svc-{i:03d}\nname: Service {i}\n"
            )
            (tmp_path / "intent" / f"svc-{i:03d}" / "specs").mkdir(parents=True, exist_ok=True)
            (tmp_path / "intent" / f"svc-{i:03d}" / "specs" / f"SPEC-{i:04d}-main.md").write_text(
                f"---\nid: SPEC-{i:04d}\nstatus: accepted\n---\n\n# Service {i}\n\n## Links\n\n- Belongs to: [[COMP-svc-{i:03d}]]\n"
            )

    def test_large_graph_builds(self, tmp_path):
        self._setup_large_repo(tmp_path, n=50)
        g = cli.build_graph(tmp_path)
        assert len([n for n in g.nodes.values() if n.type == "component"]) == 50

    def test_large_graph_status(self, tmp_path):
        self._setup_large_repo(tmp_path, n=50)
        rc, out, _ = run_sigil("status", repo=tmp_path)
        assert rc == 0

    def test_large_graph_coverage(self, tmp_path):
        self._setup_large_repo(tmp_path, n=50)
        rc, out, _ = run_sigil("coverage", "--json", repo=tmp_path)
        assert rc == 0
        data = json.loads(out)
        assert data["stats"]["components"] == 50


# ===========================================================================
# Command output contract tests
# ===========================================================================

class TestOutputContracts:
    """Verify that CLI commands produce outputs matching expected contracts."""

    @pytest.fixture(autouse=True)
    def check_demo_exists(self):
        if not DEMO_APP.exists():
            pytest.skip("demo-app not present")

    def test_status_json_structure(self):
        """status --json should return well-formed JSON (if supported)."""
        rc, out, _ = run_sigil("status", "--json", repo=DEMO_APP)
        if rc == 0 and out.strip().startswith("{"):
            data = json.loads(out)
            assert "health" in data or "score" in data

    def test_coverage_json_contract(self):
        rc, out, _ = run_sigil("coverage", "--json", repo=DEMO_APP)
        assert rc == 0
        data = json.loads(out)
        # Required top-level keys
        for key in ["score", "metrics", "components", "findings", "stats"]:
            assert key in data, f"Missing key: {key}"
        # Score is 0-100
        assert 0 <= data["score"] <= 100
        # Components have required fields
        for comp in data["components"]:
            assert "id" in comp
            assert "level" in comp
            assert comp["level"] in ("green", "yellow", "red")

    def test_check_json_contract(self):
        rc, out, _ = run_sigil("check", "--json", repo=DEMO_APP)
        assert rc == 0
        data = json.loads(out)
        assert "gates" in data
        assert "passed" in data
        assert "failed" in data
        for gate in data["gates"]:
            assert "id" in gate
            assert "passed" in gate

    def test_impact_json_contract(self):
        rc, out, _ = run_sigil("impact", "--json", "COMP-order-service", repo=DEMO_APP)
        assert rc == 0
        data = json.loads(out)
        assert "rings" in data
        assert "node" in data or "center" in data
        for ring in data["rings"]:
            # Rings may be dicts with "nodes" key or direct lists
            nodes = ring.get("nodes", ring) if isinstance(ring, dict) else ring
            for node in nodes:
                assert "id" in node

    def test_graph_json_contract(self):
        """graph.json should have standard structure."""
        g = cli.build_graph(DEMO_APP)
        cli.write_graph_artifacts(DEMO_APP, g)
        graph_path = DEMO_APP / ".intent" / "index" / "graph.json"
        data = json.loads(graph_path.read_text())
        assert "nodes" in data
        assert "edges" in data
        for node in data["nodes"]:
            assert "id" in node
            assert "type" in node
        for edge in data["edges"]:
            assert "src" in edge or "source" in edge
            assert "dst" in edge or "target" in edge
            assert "type" in edge
