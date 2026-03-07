"""Tests for graph building."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_repo(tmp_path: Path) -> Path:
    """Create a minimal repo structure for testing."""
    (tmp_path / "components").mkdir()
    (tmp_path / "intent" / "mycomp" / "specs").mkdir(parents=True)
    (tmp_path / "intent" / "mycomp" / "adrs").mkdir(parents=True)
    (tmp_path / "interfaces").mkdir()
    (tmp_path / "gates").mkdir()
    return tmp_path


def test_build_graph_empty_repo(tmp_path):
    g = cli.build_graph(tmp_path)
    assert isinstance(g.nodes, dict)
    assert isinstance(g.edges, list)
    assert len(g.nodes) == 0


def test_discover_components(tmp_path):
    (tmp_path / "components").mkdir()
    comp_yaml = tmp_path / "components" / "auth.yaml"
    comp_yaml.write_text("id: COMP-auth\nname: Auth Service\n", encoding="utf-8")
    nodes = cli.discover_components(tmp_path)
    assert "COMP-auth" in nodes
    assert nodes["COMP-auth"].type == "component"
    assert nodes["COMP-auth"].title == "Auth Service"


def test_discover_components_fallback_id(tmp_path):
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "billing.yaml").write_text("name: Billing\n", encoding="utf-8")
    nodes = cli.discover_components(tmp_path)
    assert "COMP-billing" in nodes


def test_discover_intent_docs_spec(tmp_path):
    (tmp_path / "intent" / "mycomp" / "specs").mkdir(parents=True)
    spec = tmp_path / "intent" / "mycomp" / "specs" / "SPEC-0001-foo.md"
    spec.write_text("---\nid: SPEC-0001\n---\n\n# Foo Spec\n\n## Intent\nTest.\n", encoding="utf-8")
    nodes = cli.discover_intent_docs(tmp_path)
    assert "SPEC-0001" in nodes
    assert nodes["SPEC-0001"].type == "spec"
    assert nodes["SPEC-0001"].title == "Foo Spec"


def test_discover_intent_docs_adr(tmp_path):
    (tmp_path / "intent" / "mycomp" / "adrs").mkdir(parents=True)
    adr = tmp_path / "intent" / "mycomp" / "adrs" / "ADR-0001-bar.md"
    adr.write_text("---\nid: ADR-0001\n---\n\n# Bar Decision\n", encoding="utf-8")
    nodes = cli.discover_intent_docs(tmp_path)
    assert "ADR-0001" in nodes
    assert nodes["ADR-0001"].type == "adr"


def test_discover_gates(tmp_path):
    (tmp_path / "gates").mkdir()
    gate = tmp_path / "gates" / "spec-quality.yaml"
    gate.write_text(
        "id: GATE-spec-quality\ndocs:\n  summary: Specs must have all sections\n  owner: platform\n",
        encoding="utf-8",
    )
    nodes = cli.discover_gates(tmp_path)
    assert "GATE-spec-quality" in nodes
    assert nodes["GATE-spec-quality"].type == "gate"


def test_build_graph_with_typed_links(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "components" / "mycomp.yaml").write_text("id: COMP-mycomp\nname: My Comp\n", encoding="utf-8")
    spec = repo / "intent" / "mycomp" / "specs" / "SPEC-0001-test.md"
    spec.write_text(
        "---\nid: SPEC-0001\n---\n\n# Test Spec\n\n## Links\n\n- Belongs to: [[COMP-mycomp]]\n",
        encoding="utf-8",
    )
    g = cli.build_graph(repo)
    assert "SPEC-0001" in g.nodes
    assert "COMP-mycomp" in g.nodes
    belongs_edges = [e for e in g.edges if e.type == "belongs_to" and e.src == "SPEC-0001"]
    assert len(belongs_edges) >= 1
    assert belongs_edges[0].dst == "COMP-mycomp"


def test_write_graph_artifacts(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "components" / "svc.yaml").write_text("id: COMP-svc\nname: Svc\n", encoding="utf-8")
    g = cli.build_graph(repo)
    cli.write_graph_artifacts(repo, g)

    graph_json = repo / ".intent" / "index" / "graph.json"
    search_json = repo / ".intent" / "index" / "search.json"
    assert graph_json.exists()
    assert search_json.exists()

    data = json.loads(graph_json.read_text())
    assert data["version"] == "1.0"
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    assert any(n["id"] == "COMP-svc" for n in data["nodes"])


def test_infer_belongs_to_from_path(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "components" / "mycomp.yaml").write_text("id: COMP-mycomp\nname: My Comp\n", encoding="utf-8")
    spec = repo / "intent" / "mycomp" / "specs" / "SPEC-0042-infer.md"
    spec.write_text("---\nid: SPEC-0042\n---\n\n# Infer Test\n\n## Intent\nTest.\n", encoding="utf-8")
    g = cli.build_graph(repo)
    inferred = [e for e in g.edges if e.src == "SPEC-0042" and e.type == "belongs_to"]
    assert len(inferred) >= 1
    assert inferred[0].dst == "COMP-mycomp"
