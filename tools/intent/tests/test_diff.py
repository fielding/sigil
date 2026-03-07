"""Tests for graph diff computation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_graph(nodes=None, edges=None) -> cli.Graph:
    return cli.Graph(
        nodes={n.id: n for n in (nodes or [])},
        edges=edges or [],
    )


def node(nid, ntype="spec", title=None, path=None):
    return cli.Node(id=nid, type=ntype, title=title or nid, path=path or f"intent/comp/specs/{nid}.md")


def edge(etype, src, dst):
    return cli.Edge(type=etype, src=src, dst=dst)


def test_diff_empty_graphs():
    d = cli.graph_diff(make_graph(), make_graph())
    assert d["nodes_added"] == []
    assert d["nodes_removed"] == []
    assert d["nodes_changed"] == []
    assert d["edges_added"] == []
    assert d["edges_removed"] == []


def test_diff_node_added():
    base = make_graph()
    head = make_graph(nodes=[node("SPEC-0001")])
    d = cli.graph_diff(base, head)
    assert "SPEC-0001" in d["nodes_added"]
    assert d["nodes_removed"] == []


def test_diff_node_removed():
    base = make_graph(nodes=[node("SPEC-0001")])
    head = make_graph()
    d = cli.graph_diff(base, head)
    assert "SPEC-0001" in d["nodes_removed"]
    assert d["nodes_added"] == []


def test_diff_node_changed_title():
    base = make_graph(nodes=[node("SPEC-0001", title="Old Title")])
    head = make_graph(nodes=[node("SPEC-0001", title="New Title")])
    d = cli.graph_diff(base, head)
    assert "SPEC-0001" in d["nodes_changed"]
    assert d["nodes_added"] == []
    assert d["nodes_removed"] == []


def test_diff_node_unchanged():
    n = node("SPEC-0001")
    base = make_graph(nodes=[n])
    head = make_graph(nodes=[node("SPEC-0001")])  # same values
    d = cli.graph_diff(base, head)
    assert d["nodes_changed"] == []


def test_diff_edge_added():
    base = make_graph()
    head = make_graph(edges=[edge("belongs_to", "SPEC-0001", "COMP-foo")])
    d = cli.graph_diff(base, head)
    assert len(d["edges_added"]) == 1
    assert d["edges_added"][0] == {"type": "belongs_to", "src": "SPEC-0001", "dst": "COMP-foo"}


def test_diff_edge_removed():
    base = make_graph(edges=[edge("belongs_to", "SPEC-0001", "COMP-foo")])
    head = make_graph()
    d = cli.graph_diff(base, head)
    assert len(d["edges_removed"]) == 1


def test_diff_edge_unchanged():
    e = edge("belongs_to", "SPEC-0001", "COMP-foo")
    base = make_graph(edges=[e])
    head = make_graph(edges=[edge("belongs_to", "SPEC-0001", "COMP-foo")])
    d = cli.graph_diff(base, head)
    assert d["edges_added"] == []
    assert d["edges_removed"] == []


def test_diff_to_markdown_no_changes():
    d = {
        "nodes_added": [], "nodes_removed": [], "nodes_changed": [],
        "edges_added": [], "edges_removed": [],
    }
    md = cli.diff_to_markdown(d, make_graph())
    assert "No intent graph changes detected." in md


def test_diff_to_markdown_with_changes():
    d = {
        "nodes_added": ["SPEC-0001"],
        "nodes_removed": [],
        "nodes_changed": [],
        "edges_added": [],
        "edges_removed": [],
    }
    g = make_graph(nodes=[node("SPEC-0001", title="My Spec")])
    md = cli.diff_to_markdown(d, g)
    assert "Nodes added" in md
    assert "SPEC-0001" in md
    assert "My Spec" in md
