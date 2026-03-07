"""Tests for the sigil ask / search_nodes functionality."""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sigil as cli


def make_args(**kwargs):
    defaults = {"repo": ".", "question": "test", "top": 5}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# _tokenize
# ---------------------------------------------------------------------------

def test_tokenize_basic():
    tokens = cli._tokenize("why did we choose PostgreSQL for storage?")
    assert "postgresql" in tokens
    assert "storage" in tokens
    # stop words filtered
    assert "why" not in tokens
    assert "did" not in tokens
    assert "we" not in tokens
    assert "for" not in tokens


def test_tokenize_empty():
    assert cli._tokenize("") == []


def test_tokenize_only_stop_words():
    assert cli._tokenize("a an the is in") == []


# ---------------------------------------------------------------------------
# _score_node
# ---------------------------------------------------------------------------

def test_score_node_title_boost():
    query = cli._tokenize("schema storage")
    # Title contains "schema" — should outscore body-only match
    title_match = cli._score_node(query, ["schema", "storage", "data"], ["schema"])
    body_only = cli._score_node(query, ["schema", "storage", "data"], ["unrelated"])
    assert title_match > body_only


def test_score_node_zero_for_no_overlap():
    query = cli._tokenize("schema")
    score = cli._score_node(query, ["database", "index"], ["unrelated"])
    assert score == 0.0


def test_score_node_empty_query():
    assert cli._score_node([], ["schema", "storage"], ["title"]) == 0.0


# ---------------------------------------------------------------------------
# _find_excerpt
# ---------------------------------------------------------------------------

def test_find_excerpt_returns_matching_line():
    body = "Introduction.\n\nWe chose PostgreSQL because it supports JSONB.\n\nOther notes."
    excerpt = cli._find_excerpt(body, ["postgresql", "jsonb"])
    assert "PostgreSQL" in excerpt or "postgresql" in excerpt.lower()


def test_find_excerpt_no_match_returns_beginning():
    body = "Line one.\nLine two.\nLine three."
    excerpt = cli._find_excerpt(body, ["xyzzy"])
    assert excerpt  # returns something


def test_find_excerpt_respects_max_chars():
    body = "word " * 200
    excerpt = cli._find_excerpt(body, ["word"], max_chars=100)
    assert len(excerpt) <= 110  # small margin for word-boundary trimming


# ---------------------------------------------------------------------------
# search_nodes
# ---------------------------------------------------------------------------

def _make_graph_with_adr(tmp_path: Path) -> tuple:
    """Create a minimal repo with one ADR about PostgreSQL."""
    (tmp_path / "intent" / "db" / "adrs").mkdir(parents=True)
    adr = tmp_path / "intent" / "db" / "adrs" / "ADR-0001-db-choice.md"
    adr.write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n"
        "# Database Choice\n\n"
        "## Context\nWe needed a relational database with JSONB support.\n\n"
        "## Decision\nWe chose PostgreSQL because it supports JSONB natively.\n\n"
        "## Consequences\nAll services must use the pg driver.\n\n"
        "## Links\n",
        encoding="utf-8",
    )
    (tmp_path / "intent" / "db" / "specs").mkdir(parents=True)
    spec = tmp_path / "intent" / "db" / "specs" / "SPEC-0001-schema.md"
    spec.write_text(
        "---\nid: SPEC-0001\nstatus: active\n---\n\n"
        "# Schema Design\n\n"
        "## Intent\nDefine the relational schema for the application.\n\n"
        "## Goals\nNormalized tables.\n\n"
        "## Non-goals\nDocument storage.\n\n"
        "## Design\nUse PostgreSQL tables with foreign keys.\n\n"
        "## Acceptance Criteria\nAll tables have primary keys.\n\n"
        "## Links\n",
        encoding="utf-8",
    )
    g = cli.build_graph(tmp_path)
    return g, tmp_path


def test_search_nodes_finds_adr_for_postgresql_question(tmp_path):
    g, repo = _make_graph_with_adr(tmp_path)
    results = cli.search_nodes("why did we choose PostgreSQL", g, repo)
    ids = [r[0] for r in results]
    assert "ADR-0001" in ids


def test_search_nodes_ranks_adr_above_spec_for_decision_question(tmp_path):
    g, repo = _make_graph_with_adr(tmp_path)
    results = cli.search_nodes("why chose PostgreSQL decision", g, repo)
    assert results, "Expected at least one result"
    assert results[0][0] == "ADR-0001"


def test_search_nodes_returns_excerpt(tmp_path):
    g, repo = _make_graph_with_adr(tmp_path)
    results = cli.search_nodes("PostgreSQL jsonb", g, repo)
    assert results
    _, score, excerpt = results[0]
    assert excerpt  # excerpt must be non-empty
    assert score > 0


def test_search_nodes_no_match(tmp_path):
    g, repo = _make_graph_with_adr(tmp_path)
    results = cli.search_nodes("xyzzy frobnicator", g, repo)
    assert results == []


def test_search_nodes_empty_graph(tmp_path):
    g = cli.build_graph(tmp_path)
    results = cli.search_nodes("schema", g, tmp_path)
    assert results == []


def test_search_nodes_respects_top_n(tmp_path):
    g, repo = _make_graph_with_adr(tmp_path)
    results = cli.search_nodes("PostgreSQL schema", g, repo, top_n=1)
    assert len(results) <= 1


# ---------------------------------------------------------------------------
# cmd_ask integration
# ---------------------------------------------------------------------------

def test_cmd_ask_prints_results(tmp_path, capsys):
    (tmp_path / "intent" / "db" / "adrs").mkdir(parents=True)
    adr = tmp_path / "intent" / "db" / "adrs" / "ADR-0001-db.md"
    adr.write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# DB Choice\n\n"
        "## Context\nChose PostgreSQL for JSONB.\n\n## Decision\nUse PostgreSQL.\n\n"
        "## Consequences\nAll services use pg.\n\n## Links\n",
        encoding="utf-8",
    )
    args = make_args(repo=str(tmp_path), question="PostgreSQL jsonb", top=5)
    rc = cli.cmd_ask(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "ADR-0001" in captured.out
    assert "Query:" in captured.out


def test_cmd_ask_no_results(tmp_path, capsys):
    (tmp_path / "intent" / "db" / "adrs").mkdir(parents=True)
    adr = tmp_path / "intent" / "db" / "adrs" / "ADR-0001-db.md"
    adr.write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# DB Choice\n\n"
        "## Context\nChose PostgreSQL.\n\n## Decision\nUse PostgreSQL.\n\n"
        "## Consequences\nAll use pg.\n\n## Links\n",
        encoding="utf-8",
    )
    args = make_args(repo=str(tmp_path), question="xyzzy frobnicator", top=5)
    rc = cli.cmd_ask(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "No matching" in captured.out


def test_cmd_ask_empty_repo(tmp_path, capsys):
    args = make_args(repo=str(tmp_path), question="anything", top=5)
    rc = cli.cmd_ask(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "No nodes" in captured.out


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def test_fuzzy_match_exact():
    assert cli._fuzzy_match("postgresql", ["postgresql", "schema"]) == 1.0


def test_fuzzy_match_typo():
    score = cli._fuzzy_match("postgrsql", ["postgresql", "schema"])
    assert score > 0.0  # should still match despite typo


def test_fuzzy_match_no_match():
    score = cli._fuzzy_match("xyzzy", ["postgresql", "schema"])
    assert score == 0.0


def test_fuzzy_match_partial():
    score = cli._fuzzy_match("postgres", ["postgresql", "schema"])
    assert score > 0.0  # partial match


# ---------------------------------------------------------------------------
# Section-aware scoring
# ---------------------------------------------------------------------------

def test_section_aware_scoring(tmp_path):
    g, repo = _make_graph_with_adr(tmp_path)
    results = cli.search_nodes("PostgreSQL jsonb", g, repo)
    assert results
    # ADR mentions PostgreSQL in Context and Decision sections (high-value)
    adr_result = [r for r in results if r[0] == "ADR-0001"]
    assert adr_result


def test_id_match_boost(tmp_path):
    g, repo = _make_graph_with_adr(tmp_path)
    results = cli.search_nodes("ADR-0001", g, repo)
    assert results
    assert results[0][0] == "ADR-0001"  # ID match should be top


def test_parse_sections():
    body = "## Context\nSome context.\n\n## Decision\nWe decided.\n\n## Links\nStuff."
    sections = cli._parse_sections(body)
    assert "context" in sections
    assert "decision" in sections
    assert "links" in sections
    assert "Some context." in sections["context"]


# ---------------------------------------------------------------------------
# Multi-word AND semantics
# ---------------------------------------------------------------------------

def test_multi_word_and_both_present(tmp_path):
    g, repo = _make_graph_with_adr(tmp_path)
    # Both "postgresql" and "jsonb" appear in the ADR
    results = cli.search_nodes("postgresql jsonb", g, repo)
    assert results
    assert any(r[0] == "ADR-0001" for r in results)


def test_multi_word_and_one_missing(tmp_path):
    g, repo = _make_graph_with_adr(tmp_path)
    # "postgresql" exists but "xyzzy" does not
    results = cli.search_nodes("postgresql xyzzy", g, repo)
    assert not any(r[0] == "ADR-0001" for r in results)


# ---------------------------------------------------------------------------
# Snippet highlighting
# ---------------------------------------------------------------------------

def test_excerpt_contains_bold_markers(tmp_path):
    g, repo = _make_graph_with_adr(tmp_path)
    results = cli.search_nodes("PostgreSQL", g, repo)
    assert results
    _, _, excerpt = results[0]
    # Bold markers: \033[1m...\033[0m
    assert "\033[1m" in excerpt


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def test_cmd_ask_json_output(tmp_path, capsys):
    (tmp_path / "intent" / "db" / "adrs").mkdir(parents=True)
    adr = tmp_path / "intent" / "db" / "adrs" / "ADR-0001-db.md"
    adr.write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# DB Choice\n\n"
        "## Context\nChose PostgreSQL for JSONB.\n\n## Decision\nUse PostgreSQL.\n\n"
        "## Consequences\nAll services use pg.\n\n## Links\n",
        encoding="utf-8",
    )
    import json
    args = make_args(repo=str(tmp_path), question="PostgreSQL", top=5, json=True)
    rc = cli.cmd_ask(args)
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "query" in data
    assert "results" in data
    assert len(data["results"]) > 0
    result = data["results"][0]
    assert "id" in result
    assert "score" in result
    assert "excerpt" in result
    # No ANSI codes in JSON excerpt
    assert "\033[" not in result["excerpt"]


def test_cmd_ask_json_no_results(tmp_path, capsys):
    import json
    (tmp_path / "intent" / "db" / "adrs").mkdir(parents=True)
    adr = tmp_path / "intent" / "db" / "adrs" / "ADR-0001-db.md"
    adr.write_text(
        "---\nid: ADR-0001\nstatus: accepted\n---\n\n# DB Choice\n\n## Context\nChose PostgreSQL.\n\n## Links\n",
        encoding="utf-8",
    )
    args = make_args(repo=str(tmp_path), question="xyzzy frobnicator", top=5, json=True)
    rc = cli.cmd_ask(args)
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["results"] == []


# ---------------------------------------------------------------------------
# search.json enrichment
# ---------------------------------------------------------------------------

def test_search_json_has_tokens(tmp_path):
    import json
    g, repo = _make_graph_with_adr(tmp_path)
    cli.write_graph_artifacts(repo, g)
    search_path = repo / ".intent" / "index" / "search.json"
    assert search_path.exists()
    data = json.loads(search_path.read_text())
    assert "nodes" in data
    for node in data["nodes"]:
        assert "title_tokens" in node
        assert "id_tokens" in node
        assert "body_tokens" in node
