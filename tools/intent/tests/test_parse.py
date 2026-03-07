"""Tests for sigil.py parsing utilities."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def test_parse_front_matter_basic():
    md = "---\nid: SPEC-0001\nstatus: accepted\n---\n\n# Title\n"
    fm, body = cli.parse_front_matter(md)
    assert fm["id"] == "SPEC-0001"
    assert fm["status"] == "accepted"
    assert "# Title" in body


def test_parse_front_matter_no_fm():
    md = "# Just a title\n\nSome content."
    fm, body = cli.parse_front_matter(md)
    assert fm == {}
    assert "Just a title" in body


def test_parse_front_matter_skips_blank_and_comments():
    md = "---\n# a comment\nid: ADR-0001\n\nstatus: proposed\n---\nBody"
    fm, body = cli.parse_front_matter(md)
    assert fm["id"] == "ADR-0001"
    assert "# a comment" not in fm


def test_parse_title_found():
    body = "\n# My Great Spec\n\nContent here."
    assert cli.parse_title(body, "fallback") == "My Great Spec"


def test_parse_title_fallback():
    body = "No heading here."
    assert cli.parse_title(body, "fallback") == "fallback"


def test_extract_wikilinks_basic():
    body = "See [[COMP-foo]] and [[SPEC-0001]] for details."
    links = cli.extract_wikilinks(body)
    assert links == ["COMP-foo", "SPEC-0001"]


def test_extract_wikilinks_dedup():
    body = "[[FOO]] and [[FOO]] again."
    assert cli.extract_wikilinks(body) == ["FOO"]


def test_extract_wikilinks_empty():
    assert cli.extract_wikilinks("no links here") == []


def test_extract_typed_links_belongs_to():
    body = "## Links\n\n- Belongs to: [[COMP-auth]]\n"
    edges = cli.extract_typed_links(body)
    assert len(edges) == 1
    e = edges[0]
    assert e.type == "belongs_to"
    assert e.dst == "COMP-auth"
    assert e.src == "__SELF__"


def test_extract_typed_links_multiple_types():
    body = "## Links\n\n- Belongs to: [[COMP-foo]]\n- Depends on: [[SPEC-0001]]\n- Provides: [[API-v1]]\n"
    edges = cli.extract_typed_links(body)
    types = {e.type for e in edges}
    assert "belongs_to" in types
    assert "depends_on" in types
    assert "provides" in types


def test_extract_typed_links_no_section():
    body = "## Context\n\nSome context.\n"
    assert cli.extract_typed_links(body) == []


def test_extract_typed_links_stops_at_next_heading():
    body = "## Links\n\n- Belongs to: [[COMP-foo]]\n\n## Other\n\n- Depends on: [[COMP-bar]]\n"
    edges = cli.extract_typed_links(body)
    dsts = {e.dst for e in edges}
    assert "COMP-foo" in dsts
    assert "COMP-bar" not in dsts


def test_extract_typed_links_multiple_ids_on_one_line():
    body = "## Links\n\n- Consumes: [[API-a]] [[API-b]]\n"
    edges = cli.extract_typed_links(body)
    dsts = {e.dst for e in edges}
    assert dsts == {"API-a", "API-b"}


def test_extract_typed_links_unknown_key_maps_to_relates_to():
    body = "## Links\n\n- related to: [[SPEC-0002]]\n"
    edges = cli.extract_typed_links(body)
    assert edges[0].type == "relates_to"
