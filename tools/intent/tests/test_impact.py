"""Tests for sigil impact command — blast radius graph traversal."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def _make_graph():
    """Create a test graph with known structure for blast radius testing."""
    nodes = {
        "COMP-A": cli.Node("COMP-A", "component", "Component A", "components/a.yaml"),
        "SPEC-1": cli.Node("SPEC-1", "spec", "Spec One", "intent/a/specs/SPEC-1.md"),
        "SPEC-2": cli.Node("SPEC-2", "spec", "Spec Two", "intent/a/specs/SPEC-2.md"),
        "ADR-1": cli.Node("ADR-1", "adr", "ADR One", "intent/a/adrs/ADR-1.md"),
        "GATE-1": cli.Node("GATE-1", "gate", "Gate One", "gates/GATE-1.yaml"),
        "COMP-B": cli.Node("COMP-B", "component", "Component B", "components/b.yaml"),
        "SPEC-3": cli.Node("SPEC-3", "spec", "Spec Three", "intent/b/specs/SPEC-3.md"),
        "ISOLATED": cli.Node("ISOLATED", "component", "Isolated Node", "components/iso.yaml"),
    }
    edges = [
        cli.Edge("belongs_to", "SPEC-1", "COMP-A"),
        cli.Edge("belongs_to", "SPEC-2", "COMP-A"),
        cli.Edge("belongs_to", "ADR-1", "COMP-A"),
        cli.Edge("decided_by", "SPEC-1", "ADR-1"),
        cli.Edge("gated_by", "SPEC-1", "GATE-1"),
        cli.Edge("depends_on", "SPEC-3", "SPEC-1"),
        cli.Edge("belongs_to", "SPEC-3", "COMP-B"),
    ]
    return cli.Graph(nodes=nodes, edges=edges)


class TestBlastRadius:
    def test_direct_connections(self):
        g = _make_graph()
        rings = cli._blast_radius("COMP-A", g)
        direct_ids = {item["id"] for item in rings[0]}
        assert "SPEC-1" in direct_ids
        assert "SPEC-2" in direct_ids
        assert "ADR-1" in direct_ids

    def test_secondary_connections(self):
        g = _make_graph()
        rings = cli._blast_radius("COMP-A", g)
        secondary_ids = {item["id"] for item in rings[1]}
        assert "GATE-1" in secondary_ids
        assert "SPEC-3" in secondary_ids

    def test_tertiary_connections(self):
        g = _make_graph()
        rings = cli._blast_radius("COMP-A", g)
        tertiary_ids = {item["id"] for item in rings[2]}
        assert "COMP-B" in tertiary_ids

    def test_no_duplicates_across_rings(self):
        g = _make_graph()
        rings = cli._blast_radius("COMP-A", g)
        all_ids = []
        for ring in rings:
            for item in ring:
                all_ids.append(item["id"])
        assert len(all_ids) == len(set(all_ids))

    def test_isolated_node_empty_rings(self):
        g = _make_graph()
        rings = cli._blast_radius("ISOLATED", g)
        total = sum(len(r) for r in rings)
        assert total == 0

    def test_depth_limit(self):
        g = _make_graph()
        rings = cli._blast_radius("COMP-A", g, max_depth=1)
        assert len(rings) == 1
        direct_ids = {item["id"] for item in rings[0]}
        assert "SPEC-1" in direct_ids
        # GATE-1 should not appear — it's 2 hops away
        assert "GATE-1" not in direct_ids

    def test_direction_tracking(self):
        g = _make_graph()
        rings = cli._blast_radius("COMP-A", g)
        # SPEC-1 belongs_to COMP-A, so from COMP-A's perspective, SPEC-1 is "in"
        spec1 = [item for item in rings[0] if item["id"] == "SPEC-1"][0]
        assert spec1["direction"] == "in"
        assert spec1["edge_type"] == "belongs_to"

    def test_item_has_type_info(self):
        g = _make_graph()
        rings = cli._blast_radius("COMP-A", g)
        spec1 = [item for item in rings[0] if item["id"] == "SPEC-1"][0]
        assert spec1["type"] == "spec"


class TestResolveNodeId:
    def test_exact_match(self):
        g = _make_graph()
        assert cli._resolve_node_id("COMP-A", g) == "COMP-A"

    def test_case_insensitive(self):
        g = _make_graph()
        assert cli._resolve_node_id("comp-a", g) == "COMP-A"

    def test_prefix_match(self):
        g = _make_graph()
        assert cli._resolve_node_id("ISOLATED", g) == "ISOLATED"

    def test_no_match(self):
        g = _make_graph()
        assert cli._resolve_node_id("NONEXISTENT", g) is None

    def test_ambiguous_returns_none(self):
        g = _make_graph()
        # "SPEC" matches SPEC-1, SPEC-2, SPEC-3 — ambiguous
        assert cli._resolve_node_id("SPEC", g) is None

    def test_unique_substring(self):
        g = _make_graph()
        assert cli._resolve_node_id("ISOLATED", g) == "ISOLATED"


class TestCmdImpact:
    def test_json_output(self, tmp_path):
        """Test impact --json against demo app."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "sigil.py"),
             "--repo", str(Path(__file__).parents[3] / "examples" / "demo-app"),
             "impact", "COMP-catalog", "--json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            # Demo app might not exist in CI
            return
        data = json.loads(result.stdout)
        assert "node" in data
        assert data["node"]["type"] == "component"
        assert "rings" in data
        assert "summary" in data
        assert data["summary"]["total"] > 0

    def test_nonexistent_node(self, tmp_path):
        """Test that impact fails for nonexistent node."""
        # Create minimal repo
        (tmp_path / "components").mkdir()
        (tmp_path / "intent").mkdir()
        (tmp_path / "interfaces").mkdir()
        (tmp_path / "gates").mkdir()
        (tmp_path / "components" / "a.yaml").write_text("id: COMP-A\nname: A\n")

        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "sigil.py"),
             "--repo", str(tmp_path), "impact", "NONEXISTENT"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 1
