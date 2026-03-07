#!/usr/bin/env python3
"""Sigil CLI — the kernel of the intent-first engineering system."""
from __future__ import annotations

import argparse
import collections
import dataclasses
import datetime as dt
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # type: ignore


# -----------------------------
# Models
# -----------------------------

@dataclasses.dataclass
class Node:
    id: str
    type: str
    title: str
    path: str
    body_summary: str = ""

@dataclasses.dataclass
class Edge:
    type: str
    src: str
    dst: str
    confidence: float = 1.0
    evidence: Optional[List[str]] = None

@dataclasses.dataclass
class Graph:
    nodes: Dict[str, Node]
    edges: List[Edge]


# -----------------------------
# Parsing
# -----------------------------

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
WIKILINK_RE = re.compile(r"\[\[([A-Za-z0-9_-]+)\]\]")


def read_text(p: Path, max_bytes: int = 400_000) -> str:
    b = p.read_bytes()[:max_bytes]
    return b.decode("utf-8", errors="replace")


def parse_front_matter(md: str) -> Tuple[Dict[str, str], str]:
    m = FRONT_MATTER_RE.match(md)
    if not m:
        return {}, md
    raw = m.group(1)
    body = md[m.end():]
    data = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    return data, body


def parse_title(md_body: str, fallback: str) -> str:
    for line in md_body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def extract_wikilinks(md_body: str) -> List[str]:
    return sorted(set(WIKILINK_RE.findall(md_body)))


def extract_typed_links(md_body: str) -> List[Edge]:
    edges: List[Edge] = []
    lines = md_body.splitlines()

    idxs = [i for i, ln in enumerate(lines) if ln.strip().lower() == "## links"]
    if not idxs:
        return edges
    i0 = idxs[0] + 1

    for i in range(i0, len(lines)):
        ln = lines[i].rstrip()
        if ln.startswith("#"):
            break
        ln_stripped = ln.strip()
        if not ln_stripped.startswith("-"):
            continue

        m = re.match(r"^-+\s*([A-Za-z ]+)\s*:\s*(.*)$", ln_stripped)
        if not m:
            continue
        key = m.group(1).strip().lower()
        rest = m.group(2)
        ids = WIKILINK_RE.findall(rest)
        if not ids:
            continue

        edge_map = {
            "belongs to": "belongs_to",
            "belongs_to": "belongs_to",
            "provides": "provides",
            "consumes": "consumes",
            "decided by": "decided_by",
            "decided_by": "decided_by",
            "depends on": "depends_on",
            "depends_on": "depends_on",
            "gates": "gated_by",
            "gated by": "gated_by",
            "gated_by": "gated_by",
            "supersedes": "supersedes",
            "for": "decided_by",
            "provided by": "provides",
            "consumed by": "consumes",
        }
        edge_type = edge_map.get(key, "relates_to")

        for d in ids:
            edges.append(Edge(type=edge_type, src="__SELF__", dst=d))

    return edges


# -----------------------------
# Discovery
# -----------------------------

def load_yaml(p: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML not installed — run: pip install pyyaml")
    return yaml.safe_load(read_text(p)) or {}


def discover_components(repo_root: Path) -> Dict[str, Node]:
    components_dir = repo_root / "components"
    nodes: Dict[str, Node] = {}
    if not components_dir.is_dir():
        return nodes
    for p in components_dir.glob("*.yaml"):
        data = load_yaml(p) if yaml else {}
        cid = data.get("id") or f"COMP-{p.stem}"
        title = data.get("name") or p.stem
        summary = data.get("description", "") or ""
        nodes[cid] = Node(id=cid, type="component", title=title,
                          path=str(p.relative_to(repo_root)).replace("\\", "/"),
                          body_summary=summary[:500])
    return nodes


def discover_interfaces(repo_root: Path) -> Dict[str, Node]:
    nodes: Dict[str, Node] = {}
    idir = repo_root / "interfaces"
    if not idir.is_dir():
        return nodes
    for child in idir.iterdir():
        if not child.is_dir():
            continue
        readme = child / "README.md"
        iid = child.name
        title = iid
        if readme.exists():
            body = read_text(readme)
            _, md = parse_front_matter(body)
            title = parse_title(md, iid)
        path = str(readme.relative_to(repo_root)).replace("\\", "/") if readme.exists() else str(child.relative_to(repo_root)).replace("\\", "/")
        nodes[iid] = Node(id=iid, type="interface", title=title, path=path)
    return nodes


def classify_intent_doc(path: Path) -> Optional[str]:
    parts = [s.lower() for s in path.parts]
    if "intent" not in parts:
        return None
    if "specs" in parts:
        return "spec"
    if "adrs" in parts:
        return "adr"
    if "risks" in parts:
        return "risk"
    if "rollouts" in parts:
        return "rollout"
    return "doc"


ID_PREFIX_BY_TYPE = {
    "spec": "SPEC-",
    "adr": "ADR-",
    "risk": "RISK-",
    "rollout": "ROLLOUT-",
}


def _extract_summary(body: str, max_chars: int = 500) -> str:
    """Extract the first meaningful section of markdown body as a summary."""
    lines = body.splitlines()
    out: list[str] = []
    length = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            continue
        out.append(line)
        length += len(line)
        if length >= max_chars:
            break
    text = "\n".join(out).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "..."
    return text


def discover_intent_docs(repo_root: Path) -> Dict[str, Node]:
    nodes: Dict[str, Node] = {}
    intent_dir = repo_root / "intent"
    if not intent_dir.is_dir():
        return nodes
    for md_path in intent_dir.rglob("*.md"):
        t = classify_intent_doc(md_path)
        if t is None:
            continue
        text = read_text(md_path)
        fm, body = parse_front_matter(text)
        doc_id = fm.get("id")
        if not doc_id:
            prefix = ID_PREFIX_BY_TYPE.get(t, "DOC-")
            m = re.search(r"(SPEC-\d+|ADR-\d+|RISK-\d+|ROLLOUT-\d+)", md_path.name, re.I)
            doc_id = m.group(1).upper() if m else f"{prefix}{md_path.stem.upper()}"
        title = parse_title(body, md_path.stem)
        summary = _extract_summary(body, 500)
        nodes[doc_id] = Node(id=doc_id, type=t, title=title,
                             path=str(md_path.relative_to(repo_root)).replace("\\", "/"),
                             body_summary=summary)
    return nodes


def discover_gates(repo_root: Path) -> Dict[str, Node]:
    nodes: Dict[str, Node] = {}
    gates_dir = repo_root / "gates"
    if not gates_dir.is_dir():
        return nodes
    for p in gates_dir.glob("*.yaml"):
        data = load_yaml(p) if yaml else {}
        gid = data.get("id") or f"GATE-{p.stem}"
        title = data.get("docs", {}).get("summary", p.stem) if isinstance(data.get("docs"), dict) else p.stem
        nodes[gid] = Node(id=gid, type="gate", title=title,
                          path=str(p.relative_to(repo_root)).replace("\\", "/"))
    return nodes


def discover_gate_edges(repo_root: Path) -> List[Edge]:
    """Extract gated_by edges from gate YAML applies_to fields."""
    edges: List[Edge] = []
    gates_dir = repo_root / "gates"
    if not gates_dir.is_dir():
        return edges
    for p in gates_dir.glob("*.yaml"):
        data = load_yaml(p) if yaml else {}
        gid = data.get("id") or f"GATE-{p.stem}"
        applies = data.get("applies_to", [])
        if isinstance(applies, list):
            for item in applies:
                if isinstance(item, dict):
                    node_ref = item.get("node")
                    if node_ref:
                        edges.append(Edge(type="gated_by", src=node_ref, dst=gid,
                                          confidence=1.0, evidence=["gate applies_to"]))
                elif isinstance(item, str):
                    edges.append(Edge(type="gated_by", src=item, dst=gid,
                                      confidence=1.0, evidence=["gate applies_to"]))
    return edges


def infer_belongs_to_edges(repo_root: Path, intent_nodes: Dict[str, Node], component_nodes: Dict[str, Node]) -> List[Edge]:
    edges: List[Edge] = []
    for nid, node in intent_nodes.items():
        p = Path(node.path)
        parts = list(p.parts)
        try:
            idx = parts.index("intent")
            comp_slug = parts[idx + 1]
        except Exception:
            continue
        comp_id_guess = f"COMP-{comp_slug}"
        if comp_id_guess in component_nodes:
            edges.append(Edge(type="belongs_to", src=nid, dst=comp_id_guess,
                              confidence=0.95, evidence=["path inference"]))
    return edges


def build_graph(repo_root: Path) -> Graph:
    nodes: Dict[str, Node] = {}
    edges: List[Edge] = []

    comp_nodes = discover_components(repo_root)
    iface_nodes = discover_interfaces(repo_root)
    intent_nodes = discover_intent_docs(repo_root)
    gate_nodes = discover_gates(repo_root)

    nodes.update(comp_nodes)
    nodes.update(iface_nodes)
    nodes.update(intent_nodes)
    nodes.update(gate_nodes)

    # Typed edges from Links blocks
    for nid, n in intent_nodes.items():
        md = read_text(repo_root / n.path)
        _, body = parse_front_matter(md)
        typed = extract_typed_links(body)
        for e in typed:
            edges.append(Edge(type=e.type, src=nid, dst=e.dst,
                              confidence=1.0, evidence=["Links block"]))

    # Inferred belongs_to
    edges.extend(infer_belongs_to_edges(repo_root, intent_nodes, comp_nodes))

    # Untyped relates_to from wikilinks
    for nid, n in intent_nodes.items():
        md = read_text(repo_root / n.path)
        _, body = parse_front_matter(md)
        for target in extract_wikilinks(body):
            if any(e.src == nid and e.dst == target for e in edges):
                continue
            if target in nodes:
                edges.append(Edge(type="relates_to", src=nid, dst=target,
                                  confidence=0.5, evidence=["wikilink"]))

    # Gate edges from applies_to
    edges.extend(discover_gate_edges(repo_root))

    return Graph(nodes=nodes, edges=edges)


def write_graph_artifacts(repo_root: Path, g: Graph) -> None:
    out_dir = repo_root / ".intent" / "index"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Enrich nodes with frontmatter for viewer features
    enriched_nodes = []
    for n in g.nodes.values():
        nd = dataclasses.asdict(n)
        if n.type in ("spec", "adr", "risk", "rollout"):
            md = read_text(repo_root / n.path)
            fm, _ = parse_front_matter(md)
            nd["frontmatter"] = fm
        enriched_nodes.append(nd)

    # Run gate checks and include results
    gate_results = _run_gate_checks(repo_root, g)

    graph_json = {
        "version": "1.0",
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nodes": enriched_nodes,
        "edges": [dataclasses.asdict(e) for e in g.edges],
        "gates": gate_results,
    }
    (out_dir / "graph.json").write_text(json.dumps(graph_json, indent=2), encoding="utf-8")

    # Write coverage.json
    cov = _compute_coverage(repo_root, g)
    (out_dir / "coverage.json").write_text(json.dumps(cov, indent=2), encoding="utf-8")

    search_nodes_list = []
    for n in g.nodes.values():
        title_tokens = _tokenize(n.title)
        id_tokens = _tokenize(n.id)
        try:
            full_text = read_text(repo_root / n.path)
        except Exception:
            full_text = ""
        _, body = parse_front_matter(full_text)
        body_tokens = _tokenize(body)
        search_nodes_list.append({
            "id": n.id, "type": n.type, "title": n.title, "path": n.path,
            "aliases": [n.title],
            "title_tokens": title_tokens,
            "id_tokens": id_tokens,
            "body_tokens": body_tokens[:200],  # cap for index size
        })
    search_json = {"nodes": search_nodes_list}
    (out_dir / "search.json").write_text(json.dumps(search_json, indent=2), encoding="utf-8")

    # Generate review.json for viewer Review mode
    try:
        _write_review_json(repo_root, g, out_dir / "review.json")
    except Exception:
        pass  # Non-critical; skip if git not available


def _write_review_json(repo_root: Path, g: Graph, out_path: Path) -> None:
    """Generate review.json with intent coverage for current working tree changes."""
    import fnmatch as fnm

    # Load component path patterns
    comp_paths: Dict[str, List[str]] = {}
    comp_dir = repo_root / "components"
    if comp_dir.is_dir():
        for p in comp_dir.glob("*.yaml"):
            data = load_yaml(p) if yaml else {}
            cid = data.get("id") or f"COMP-{p.stem}"
            paths = data.get("paths", [])
            if isinstance(paths, list):
                comp_paths[cid] = paths

    # Get changed files
    try:
        diff_out = run_cmd(["git", "-C", str(repo_root), "diff", "--name-status", "HEAD"], cwd=repo_root)
    except Exception:
        try:
            diff_out = run_cmd(["git", "-C", str(repo_root), "status", "--porcelain"], cwd=repo_root)
            lines = []
            for line in diff_out.strip().split("\n"):
                if line.strip():
                    code = line[:2].strip() or "A"
                    fpath = line[3:].strip()
                    lines.append(f"{code[0]}\t{fpath}")
            diff_out = "\n".join(lines)
        except Exception:
            diff_out = ""

    changes = []
    skip_prefixes = [".intent/index/", ".git/", "templates/", ".pytest_cache/"]
    intent_prefixes = ["components/", "intent/", "interfaces/", "gates/"]

    for line in diff_out.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            changes.append((parts[0].strip()[0] if parts[0].strip() else "M", parts[1].strip()))

    intent_changes = []
    code_changes = []
    for status, fpath in changes:
        if any(fpath.startswith(sp) for sp in skip_prefixes):
            continue
        if any(fpath.startswith(ip) for ip in intent_prefixes):
            intent_changes.append({"status": status, "path": fpath})
        else:
            code_changes.append({"status": status, "path": fpath})

    # Map to components
    covered = {}
    uncovered = []
    for item in code_changes:
        fpath = item["path"]
        matched = False
        for cid, patterns in comp_paths.items():
            for pat in patterns:
                if fnm.fnmatch(fpath, pat):
                    covered.setdefault(cid, []).append(item)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            uncovered.append(item)

    covered_count = sum(len(v) for v in covered.values())
    coverage_pct = round(covered_count / max(len(code_changes), 1) * 100) if code_changes else 100

    # Build per-component governance info
    governance = {}
    for cid in covered:
        specs = []
        adrs = []
        gates_list = []
        for e in g.edges:
            if e.dst == cid and e.type == "belongs_to":
                node = g.nodes.get(e.src)
                if node:
                    if node.type == "spec":
                        md = read_text(repo_root / node.path)
                        fm, _ = parse_front_matter(md)
                        specs.append({"id": e.src, "title": node.title, "status": fm.get("status", "?")})
                    elif node.type == "adr":
                        md = read_text(repo_root / node.path)
                        fm, _ = parse_front_matter(md)
                        adrs.append({"id": e.src, "title": node.title, "status": fm.get("status", "?")})
            if e.type == "gated_by" and (e.src == cid or e.dst == cid):
                gid = e.dst if e.src == cid else e.src
                gnode = g.nodes.get(gid)
                if gnode:
                    gates_list.append({"id": gid, "title": gnode.title})
        governance[cid] = {"specs": specs, "adrs": adrs, "gates": gates_list}

    # Gate results
    gate_results = _run_gate_checks(repo_root, g)

    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_changes": len(changes),
            "intent_changes": len(intent_changes),
            "code_changes": len(code_changes),
            "covered_files": covered_count,
            "uncovered_files": len(uncovered),
            "coverage_pct": coverage_pct,
        },
        "intent_changes": intent_changes,
        "covered": {cid: files for cid, files in covered.items()},
        "uncovered": uncovered,
        "governance": governance,
        "gates": gate_results,
    }
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


# -----------------------------
# Viewer resolution
# -----------------------------

def _find_viewer(repo: Path) -> Optional[Path]:
    """Find the viewer HTML — in-repo first, then bundled with pip package."""
    in_repo = repo / "tools" / "intent_viewer" / "index.html"
    if in_repo.exists():
        return in_repo
    # Check next to this script (pip force-include puts it as sibling)
    bundled = Path(__file__).with_name("sigil_viewer.html")
    if bundled.exists():
        return bundled
    # Check via importlib
    import importlib.util
    spec = importlib.util.find_spec("sigil_cli")
    if spec and spec.origin:
        candidate = Path(spec.origin).with_name("sigil_viewer.html")
        if candidate.exists():
            return candidate
    return None


def _ensure_viewer(repo: Path) -> Optional[Path]:
    """Ensure viewer exists in repo. Copy from package if needed. Return path."""
    in_repo = repo / "tools" / "intent_viewer" / "index.html"
    if in_repo.exists():
        return in_repo
    src = _find_viewer(repo)
    if src and src != in_repo:
        in_repo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, in_repo)
        return in_repo
    return None


# -----------------------------
# Git helpers for diff
# -----------------------------

def run_cmd(cmd: List[str], cwd: Optional[Path] = None) -> str:
    p = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{p.stderr}")
    return p.stdout


def checkout_tree(repo_root: Path, sha: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    try:
        run_cmd(["bash", "-lc",
                 f"git -C {repo_root} archive {sha} components intent interfaces gates .intent 2>/dev/null | tar -x -C {dest}"])
    except Exception:
        run_cmd(["bash", "-lc",
                 f"git -C {repo_root} archive {sha} | tar -x -C {dest}"])


def graph_diff(base: Graph, head: Graph) -> dict:
    base_nodes = set(base.nodes.keys())
    head_nodes = set(head.nodes.keys())

    def edge_key(e: Edge) -> Tuple[str, str, str]:
        return (e.type, e.src, e.dst)

    base_edges = set(edge_key(e) for e in base.edges)
    head_edges = set(edge_key(e) for e in head.edges)

    nodes_added = sorted(head_nodes - base_nodes)
    nodes_removed = sorted(base_nodes - head_nodes)
    nodes_changed = []
    for nid in sorted(base_nodes & head_nodes):
        b = base.nodes[nid]
        h = head.nodes[nid]
        if (b.type, b.title, b.path) != (h.type, h.title, h.path):
            nodes_changed.append(nid)

    edges_added = sorted(list(head_edges - base_edges))
    edges_removed = sorted(list(base_edges - head_edges))

    return {
        "nodes_added": nodes_added,
        "nodes_removed": nodes_removed,
        "nodes_changed": nodes_changed,
        "edges_added": [{"type": t, "src": s, "dst": d} for (t, s, d) in edges_added],
        "edges_removed": [{"type": t, "src": s, "dst": d} for (t, s, d) in edges_removed],
    }


def diff_to_markdown(d: dict, head_graph: Graph) -> str:
    def title(nid: str) -> str:
        n = head_graph.nodes.get(nid)
        return n.title if n else nid

    lines = ["## Intent Graph Diff", ""]
    if d["nodes_added"]:
        lines.append("### Nodes added")
        for nid in d["nodes_added"]:
            lines.append(f"- `{nid}` ({title(nid)})")
        lines.append("")
    if d["nodes_changed"]:
        lines.append("### Nodes changed")
        for nid in d["nodes_changed"]:
            lines.append(f"- `{nid}` ({title(nid)})")
        lines.append("")
    if d["nodes_removed"]:
        lines.append("### Nodes removed")
        for nid in d["nodes_removed"]:
            lines.append(f"- `{nid}`")
        lines.append("")
    if d["edges_added"]:
        lines.append("### Edges added")
        for e in d["edges_added"]:
            lines.append(f"- `{e['src']}` **{e['type']}** -> `{e['dst']}`")
        lines.append("")
    if d["edges_removed"]:
        lines.append("### Edges removed")
        for e in d["edges_removed"]:
            lines.append(f"- `{e['src']}` **{e['type']}** -> `{e['dst']}`")
        lines.append("")

    if not any(d[k] for k in ["nodes_added", "nodes_changed", "nodes_removed", "edges_added", "edges_removed"]):
        lines.append("No intent graph changes detected.")
        lines.append("")

    lines.append("> Generated by `sigil diff`.")
    return "\n".join(lines)


# -----------------------------
# Ask / search
# -----------------------------

_STOP_WORDS = {
    "a", "an", "the", "is", "in", "it", "of", "to", "and", "or", "for",
    "with", "this", "that", "was", "are", "be", "by", "at", "as", "from",
    "on", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "not", "we", "our", "my",
    "i", "you", "he", "she", "they", "them", "their", "its", "us",
    "so", "but", "if", "then", "than", "also", "any", "all", "no",
    "why", "what", "how", "when", "where", "who", "which",
}


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z0-9]+", text)
            if t.lower() not in _STOP_WORDS and len(t) > 1]


def _fuzzy_match(token: str, candidates: List[str], threshold: float = 0.75) -> float:
    """Return best fuzzy match ratio for token against candidate list."""
    from difflib import SequenceMatcher
    best = 0.0
    for c in candidates:
        if token == c:
            return 1.0
        if abs(len(token) - len(c)) > max(len(token), len(c)) * 0.4:
            continue
        ratio = SequenceMatcher(None, token, c).ratio()
        if ratio > best:
            best = ratio
    return best if best >= threshold else 0.0


def _parse_sections(body: str) -> Dict[str, str]:
    """Split markdown body into named sections by ## headings."""
    sections: Dict[str, str] = {}
    current_name = "_preamble"
    current_lines: List[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections[current_name] = "\n".join(current_lines)
            current_name = line[3:].strip().lower()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections[current_name] = "\n".join(current_lines)
    return sections


# Section weights for ranking
_SECTION_WEIGHTS = {
    "context": 2.0, "intent": 2.0, "decision": 1.5, "design": 1.5,
    "goals": 1.5, "non-goals": 1.0, "consequences": 1.0, "alternatives": 1.0,
    "acceptance criteria": 1.0, "links": 0.3, "_preamble": 0.5,
}


def _score_node(query_tokens: List[str], body_tokens: List[str], title_tokens: List[str],
                nid: str = "", sections: Optional[Dict[str, str]] = None) -> float:
    """Section-aware scoring with fuzzy matching, title/id boost, and AND semantics."""
    if not query_tokens:
        return 0.0

    # Check AND semantics: all query tokens must match somewhere (exact or fuzzy)
    all_searchable = set(title_tokens + body_tokens + _tokenize(nid))
    matched_tokens = []
    for qt in query_tokens:
        if qt in all_searchable:
            matched_tokens.append(qt)
        elif _fuzzy_match(qt, list(all_searchable)) > 0:
            matched_tokens.append(qt)

    if len(matched_tokens) < len(query_tokens):
        return 0.0  # AND: all tokens must match

    score = 0.0
    id_tokens = set(_tokenize(nid))

    # ID match boost (5x)
    for qt in query_tokens:
        if qt in id_tokens:
            score += 5.0
        elif _fuzzy_match(qt, list(id_tokens)) > 0:
            score += 3.0

    # Title match boost (3x)
    title_set = set(title_tokens)
    for qt in query_tokens:
        if qt in title_set:
            score += 3.0
        elif _fuzzy_match(qt, list(title_set)) > 0:
            score += 1.5

    # Section-aware body scoring
    if sections:
        for sec_name, sec_text in sections.items():
            sec_tokens = _tokenize(sec_text)
            if not sec_tokens:
                continue
            weight = _SECTION_WEIGHTS.get(sec_name, 0.8)
            sec_counter = collections.Counter(sec_tokens)
            total = max(len(sec_tokens), 1)
            for qt in query_tokens:
                tf = sec_counter.get(qt, 0) / total
                if tf > 0:
                    score += tf * weight
                else:
                    fuzzy = _fuzzy_match(qt, list(sec_counter.keys()))
                    if fuzzy > 0:
                        score += (fuzzy * 0.5) * weight / total
    else:
        # Fallback: flat body scoring
        body_counter = collections.Counter(body_tokens)
        total_body = max(len(body_tokens), 1)
        for qt in query_tokens:
            tf = body_counter.get(qt, 0) / total_body
            score += tf

    return score


def _find_excerpt(body: str, query_tokens: List[str], max_chars: int = 300) -> str:
    """Return the 2-3 lines most relevant to query_tokens with term highlighting."""
    lines = body.splitlines()
    if not lines:
        return ""
    query_set = set(query_tokens)
    best_score = -1
    best_idx = 0
    for i, line in enumerate(lines):
        tokens = set(re.findall(r"[A-Za-z0-9]+", line.lower()))
        s = len(tokens & query_set)
        # Also count fuzzy matches
        if s == 0:
            for qt in query_set:
                if _fuzzy_match(qt, list(tokens)) > 0:
                    s += 0.5
        if s > best_score:
            best_score = s
            best_idx = i
    if best_score <= 0:
        return " ".join(lines[:3])[:max_chars]
    start = max(0, best_idx - 1)
    end = min(len(lines), best_idx + 3)
    excerpt_lines = lines[start:end]

    # Highlight matching terms with bold markers
    highlighted = []
    for line in excerpt_lines:
        for qt in query_tokens:
            pattern = re.compile(re.escape(qt), re.IGNORECASE)
            line = pattern.sub(lambda m: f"\033[1m{m.group()}\033[0m", line)
        highlighted.append(line)

    excerpt = "\n".join(highlighted).strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rsplit(" ", 1)[0] + "..."
    return excerpt


def search_nodes(query: str, graph: Graph, repo_root: Path,
                 top_n: int = 5) -> List[Tuple[str, float, str]]:
    """Search graph nodes by relevance. Returns [(node_id, score, excerpt)]."""
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    results = []
    for nid, node in graph.nodes.items():
        try:
            full_text = read_text(repo_root / node.path)
        except Exception:
            full_text = node.title + " " + node.body_summary
        _, body = parse_front_matter(full_text)
        body_tokens = _tokenize(body)
        title_tokens = _tokenize(node.title)
        sections = _parse_sections(body)
        score = _score_node(query_tokens, body_tokens, title_tokens, nid=nid, sections=sections)
        if score > 0:
            excerpt = _find_excerpt(body, query_tokens)
            results.append((nid, score, excerpt))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_n]


def cmd_ask(args) -> int:
    repo = Path(args.repo).resolve()
    question = args.question
    top_n = getattr(args, "top", 5)
    output_json = getattr(args, "json", False)

    g = build_graph(repo)
    if not g.nodes:
        print("No nodes found. Run `sigil index` to build the graph.")
        return 0

    results = search_nodes(question, g, repo, top_n=top_n)
    if not results:
        if output_json:
            print(json.dumps({"query": question, "results": []}))
        else:
            print("No matching nodes found.")
        return 0

    if output_json:
        json_results = []
        for nid, score, excerpt in results:
            node = g.nodes[nid]
            # Strip ANSI codes from excerpt for JSON
            clean_excerpt = re.sub(r'\033\[[0-9;]*m', '', excerpt)
            json_results.append({
                "id": nid,
                "type": node.type,
                "title": node.title,
                "path": node.path,
                "score": round(score, 3),
                "excerpt": clean_excerpt,
            })
        print(json.dumps({"query": question, "results": json_results}, indent=2))
        return 0

    # Terminal output with type badges and scores
    type_badges = {
        "spec": "\033[34mSPEC\033[0m",
        "adr": "\033[33mADR\033[0m",
        "component": "\033[32mCOMP\033[0m",
        "gate": "\033[35mGATE\033[0m",
        "interface": "\033[36mIFACE\033[0m",
        "risk": "\033[31mRISK\033[0m",
        "rollout": "\033[33mROLL\033[0m",
    }

    print(f"\n  Query: {question}")
    print(f"  {len(results)} result(s)\n")
    for nid, score, excerpt in results:
        node = g.nodes[nid]
        badge = type_badges.get(node.type, node.type.upper())
        print(f"  [{badge}] \033[1m{nid}\033[0m  {node.title}  (score: {score:.2f})")
        print(f"    {node.path}")
        if excerpt:
            for line in excerpt.splitlines():
                print(f"    | {line}")
        print()
    return 0


# -----------------------------
# CLI commands
# -----------------------------

def cmd_status(args) -> int:
    """Print a concise status report of the intent graph's health."""
    repo = Path(args.repo).resolve()
    g = build_graph(repo)

    types: Dict[str, int] = {}
    for n in g.nodes.values():
        types[n.type] = types.get(n.type, 0) + 1

    edge_types: Dict[str, int] = {}
    for e in g.edges:
        edge_types[e.type] = edge_types.get(e.type, 0) + 1

    # Health scoring (same algorithm as viewer)
    components = [n for n in g.nodes.values() if n.type == "component"]
    specs = [n for n in g.nodes.values() if n.type == "spec"]
    adrs = [n for n in g.nodes.values() if n.type == "adr"]
    gates = [n for n in g.nodes.values() if n.type == "gate"]

    comps_with_spec = set()
    for e in g.edges:
        if e.type == "belongs_to":
            comps_with_spec.add(e.dst)

    # Check statuses
    accepted_adrs = 0
    draft_adrs = 0
    for nid, n in g.nodes.items():
        if n.type != "adr":
            continue
        md = read_text(repo / n.path)
        fm, _ = parse_front_matter(md)
        if fm.get("status") in ("accepted", "active"):
            accepted_adrs += 1
        elif fm.get("status") in ("draft", "proposed"):
            draft_adrs += 1

    node_ids = set(g.nodes.keys())
    dangling = sum(1 for e in g.edges if e.dst not in node_ids)

    # Compute score
    score = 0.0
    max_score = 0.0
    if components:
        score += (len(comps_with_spec & set(n.id for n in components)) / len(components)) * 40
        max_score += 40
    if adrs:
        score += (accepted_adrs / len(adrs)) * 30
        max_score += 30
    if specs:
        max_score += 20
        score += 20  # Simplified: all have status
    if g.edges:
        clean = len(g.edges) - dangling
        score += (clean / len(g.edges)) * 10
        max_score += 10
    pct = round((score / max_score) * 100) if max_score > 0 else 0

    # Output
    bar_len = 20
    filled = round(pct / 100 * bar_len)
    bar = "#" * filled + "-" * (bar_len - filled)

    print()
    print(f"  Sigil Intent Status")
    print(f"  ====================")
    print(f"  Health: [{bar}] {pct}%")
    print()
    print(f"  Nodes: {len(g.nodes)}")
    for t in ["component", "spec", "adr", "gate", "interface"]:
        if types.get(t, 0):
            print(f"    {t}: {types[t]}")
    print(f"  Edges: {len(g.edges)}")
    for et in sorted(edge_types, key=lambda k: -edge_types[k]):
        print(f"    {et}: {edge_types[et]}")
    print()

    issues = []
    uncomps = [n for n in components if n.id not in comps_with_spec]
    if uncomps:
        issues.append(f"  {len(uncomps)} component(s) have no governing spec")
    if draft_adrs:
        issues.append(f"  {draft_adrs} ADR(s) still in draft/proposed")
    if dangling:
        issues.append(f"  {dangling} dangling reference(s)")

    if issues:
        print("  Issues:")
        for i in issues:
            print(f"    - {i}")
    else:
        print("  No issues found.")
    print()
    return 0


def cmd_index(args) -> int:
    repo = Path(args.repo).resolve()
    g = build_graph(repo)
    write_graph_artifacts(repo, g)
    print(f"Indexed {len(g.nodes)} nodes, {len(g.edges)} edges")
    print("Wrote .intent/index/graph.json and search.json")
    return 0


def cmd_diff(args) -> int:
    repo = Path(args.repo).resolve()
    with tempfile.TemporaryDirectory() as td:
        base_dir = Path(td) / "base"
        head_dir = Path(td) / "head"
        checkout_tree(repo, args.base, base_dir)
        checkout_tree(repo, args.head, head_dir)

        g_base = build_graph(base_dir)
        g_head = build_graph(head_dir)
        d = graph_diff(g_base, g_head)

        if args.out:
            Path(args.out).write_text(json.dumps(d, indent=2), encoding="utf-8")
        md = diff_to_markdown(d, g_head)
        if args.md:
            Path(args.md).write_text(md, encoding="utf-8")
        print(md)
    return 0


def cmd_new(args) -> int:
    repo = Path(args.repo).resolve()
    node_type = args.type
    component = args.component
    title = args.title

    templates_dir = repo / "templates"
    config_path = repo / ".intent" / "config.yaml"

    # Read config for next ID
    next_num = 1
    if config_path.exists() and yaml:
        cfg = load_yaml(config_path)
        counters = cfg.get("id_counters", {})
        prefix = node_type.upper()
        next_num = counters.get(prefix, 0) + 1

    type_to_template = {
        "spec": "SPEC.md",
        "adr": "ADR.md",
    }
    template_file = type_to_template.get(node_type)
    if not template_file:
        print(f"Unknown type: {node_type}. Supported: spec, adr")
        return 1

    template_path = templates_dir / template_file
    if not template_path.exists():
        print(f"Template not found: {template_path}")
        return 1

    prefix = node_type.upper()
    node_id = f"{prefix}-{next_num:04d}"
    slug = title.lower().replace(" ", "-").replace("/", "-")
    filename = f"{node_id}-{slug}.md"

    subdir_map = {"spec": "specs", "adr": "adrs"}
    subdir = subdir_map.get(node_type, node_type + "s")
    dest_dir = repo / "intent" / component / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename

    content = read_text(template_path)
    content = content.replace(f"{prefix}-0000", node_id)
    content = content.replace("<Title>", title)
    content = content.replace("<Decision>", title)
    content = content.replace("<component>", component)

    dest.write_text(content, encoding="utf-8")

    # Persist the updated counter so the next `sigil new` gets a fresh ID
    if yaml and config_path.exists():
        cfg = load_yaml(config_path)
        counters = cfg.get("id_counters", {})
        counters[prefix] = next_num
        cfg["id_counters"] = counters
        config_path.write_text(yaml.dump(cfg, default_flow_style=False), encoding="utf-8")
    elif yaml:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.dump({"id_counters": {prefix: next_num}}, default_flow_style=False), encoding="utf-8")

    print(f"Created {dest.relative_to(repo)}")
    print(f"  ID: {node_id}")
    return 0


VALID_STATUSES = {"draft", "proposed", "accepted", "rejected", "deprecated", "active", "superseded"}

LINT_SEVERITIES = {"error", "warn", "info"}


def _lint_emit(items: List[Tuple[str, str, str]], severity: str, node_id: str, msg: str) -> None:
    items.append((severity, node_id, msg))


def cmd_lint(args) -> int:
    repo = Path(args.repo).resolve()
    g = build_graph(repo)
    min_severity = getattr(args, "min_severity", "warn")

    severity_rank = {"error": 0, "warn": 1, "info": 2}
    min_rank = severity_rank.get(min_severity, 1)

    findings: List[Tuple[str, str, str]] = []  # (severity, id, message)

    for nid, node in g.nodes.items():
        if node.type not in ("spec", "adr"):
            continue
        md = read_text(repo / node.path)
        fm, body = parse_front_matter(md)

        # ID must be present in front matter
        if not fm.get("id"):
            _lint_emit(findings, "error", nid, "missing 'id' field in front matter")

        # ID must match node id
        elif fm.get("id") != nid:
            _lint_emit(findings, "error", nid, f"front matter id '{fm['id']}' does not match derived id '{nid}'")

        # Status field
        status = fm.get("status", "")
        if not status:
            _lint_emit(findings, "warn", nid, "missing 'status' field in front matter")
        elif status not in VALID_STATUSES:
            _lint_emit(findings, "warn", nid, f"unknown status '{status}' (expected: {', '.join(sorted(VALID_STATUSES))})")

        if node.type == "spec":
            required = ["Intent", "Goals", "Non-goals", "Design", "Acceptance Criteria", "Links"]
            for section in required:
                if f"## {section}" not in body:
                    _lint_emit(findings, "warn", nid, f"missing section '## {section}'")

            # Check for belongs_to link
            typed = extract_typed_links(body)
            has_belongs_to = any(e.type == "belongs_to" for e in typed)
            if not has_belongs_to:
                inferred = any(e.src == nid and e.type == "belongs_to" for e in g.edges)
                if not inferred:
                    _lint_emit(findings, "warn", nid, "no 'Belongs to' link (explicit or inferred)")

        if node.type == "adr":
            required = ["Context", "Decision", "Consequences", "Links"]
            for section in required:
                if f"## {section}" not in body:
                    _lint_emit(findings, "warn", nid, f"missing section '## {section}'")

    # Dangling references
    all_ids = set(g.nodes.keys())
    for e in g.edges:
        if e.dst not in all_ids:
            _lint_emit(findings, "warn", e.src, f"dangling reference -> {e.dst}")

    # Filter and print
    warnings = 0
    errors = 0
    for sev, nid, msg in sorted(findings, key=lambda x: (severity_rank.get(x[0], 99), x[1])):
        rank = severity_rank.get(sev, 99)
        if rank > min_rank:
            continue
        label = sev.upper()
        print(f"{label} {nid}: {msg}")
        if sev == "error":
            errors += 1
        else:
            warnings += 1

    print(f"\nLint: {warnings} warning(s), {errors} error(s)")
    return 1 if errors > 0 else 0


def cmd_fmt(args) -> int:
    """Normalize intent documents: ensure front matter has id, insert ## Links section if missing."""
    repo = Path(args.repo).resolve()
    intent_dir = repo / "intent"
    if not intent_dir.is_dir():
        print("No intent/ directory found.")
        return 0

    changed = 0
    checked = 0

    for md_path in sorted(intent_dir.rglob("*.md")):
        t = classify_intent_doc(md_path)
        if t is None:
            continue
        checked += 1
        text = read_text(md_path)
        fm, body = parse_front_matter(text)
        original = text

        # Derive canonical ID from filename if not in front matter
        if not fm.get("id"):
            prefix = ID_PREFIX_BY_TYPE.get(t, "DOC-")
            m = re.search(r"(SPEC-\d+|ADR-\d+|RISK-\d+|ROLLOUT-\d+)", md_path.name, re.I)
            derived_id = m.group(1).upper() if m else None
            if derived_id:
                # Insert id into front matter
                if FRONT_MATTER_RE.match(text):
                    text = FRONT_MATTER_RE.sub(
                        lambda mo: f"---\nid: {derived_id}\n{mo.group(1)}\n---\n",
                        text, count=1
                    )
                else:
                    text = f"---\nid: {derived_id}\n---\n\n" + text
                fm["id"] = derived_id

        # Ensure ## Links section exists
        _, cur_body = parse_front_matter(text)
        has_links = any(ln.strip().lower() == "## links" for ln in cur_body.splitlines())
        if not has_links:
            if text.endswith("\n"):
                text = text + "\n## Links\n\n"
            else:
                text = text + "\n\n## Links\n\n"

        if text != original:
            md_path.write_text(text, encoding="utf-8")
            print(f"fmt {md_path.relative_to(repo)}")
            changed += 1

    print(f"\nfmt: checked {checked} file(s), updated {changed}")
    return 0


# Patterns used by bootstrap to detect source components
_MANIFEST_PATTERNS = [
    ("package.json", "js"),
    ("pyproject.toml", "python"),
    ("setup.py", "python"),
    ("go.mod", "go"),
    ("Cargo.toml", "rust"),
    ("pom.xml", "java"),
    ("build.gradle", "java"),
]

_SKIP_DIRS = {".git", ".intent", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def cmd_bootstrap(args) -> int:
    """Scan repo heuristically and create missing COMPONENT.yaml stubs."""
    repo = Path(args.repo).resolve()
    dry_run = getattr(args, "dry_run", False)

    # Collect existing component ids/names from the registry
    existing_paths = set()
    components_dir = repo / "components"
    if components_dir.is_dir():
        for p in components_dir.glob("*.yaml"):
            existing_paths.add(p.stem)

    discovered: List[Tuple[str, str, str]] = []  # (slug, lang, detected_via)

    for child in sorted(repo.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name in _SKIP_DIRS:
            continue
        # Check for manifest files
        for manifest, lang in _MANIFEST_PATTERNS:
            if (child / manifest).exists():
                slug = child.name.lower().replace(" ", "-")
                discovered.append((slug, lang, manifest))
                break

    if not discovered:
        print("No source components detected (no package.json, pyproject.toml, go.mod, etc. found in top-level dirs).")
        return 0

    created = 0
    skipped = 0

    for slug, lang, via in discovered:
        if slug in existing_paths:
            print(f"skip  {slug}  (components/{slug}.yaml already exists)")
            skipped += 1
            continue

        comp_id = f"COMP-{slug}"
        yaml_content = (
            f"id: {comp_id}\n"
            f"name: {slug.replace('-', ' ').title()}\n"
            f"lang: {lang}\n"
            f"status: active\n"
            f"# bootstrapped from {via}\n"
        )
        dest = components_dir / f"{slug}.yaml"

        if dry_run:
            print(f"[dry-run] would create  {dest.relative_to(repo)}")
        else:
            components_dir.mkdir(exist_ok=True)
            dest.write_text(yaml_content, encoding="utf-8")
            print(f"created  {dest.relative_to(repo)}")
        created += 1

    action = "would create" if dry_run else "created"
    print(f"\nbootstrap: {action} {created} component(s), skipped {skipped}")
    return 0


def cmd_init(args) -> int:
    """Zero-to-working setup: create dirs, bootstrap components, index, and open viewer."""
    repo = Path(args.repo).resolve()

    print()
    print("  ┌─────────────────────────────────────┐")
    print("  │         SIGIL — init                 │")
    print("  │   Intent-first engineering system    │")
    print("  └─────────────────────────────────────┘")
    print()

    # Create directory structure
    dirs = ["components", "intent", "interfaces", "gates", "templates", ".intent"]
    created_dirs = 0
    for d in dirs:
        p = repo / d
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created_dirs += 1
    if created_dirs:
        print(f"  [1/6] Created {created_dirs} directories")
    else:
        print(f"  [1/6] Directory structure exists")

    # Create .intent/config.yaml if missing
    config_path = repo / ".intent" / "config.yaml"
    if not config_path.exists():
        config_path.write_text("# Sigil intent system config\nid_counters: {}\n", encoding="utf-8")

    # Create default templates if missing
    templates_dir = repo / "templates"
    spec_tmpl = templates_dir / "SPEC.md"
    adr_tmpl = templates_dir / "ADR.md"
    if not spec_tmpl.exists():
        spec_tmpl.write_text(
            "---\nid: SPEC-0000\nstatus: draft\n---\n\n# <Title>\n\n## Intent\n\nWhat are we building and why?\n\n"
            "## Goals\n\n- \n\n## Non-goals\n\n- \n\n## Design\n\n## Acceptance Criteria\n\n- [ ] \n\n## Links\n\n"
            "- Belongs to: [[COMP-<component>]]\n", encoding="utf-8")
    if not adr_tmpl.exists():
        adr_tmpl.write_text(
            "---\nid: ADR-0000\nstatus: draft\n---\n\n# <Decision>\n\n## Context\n\nWhat is the background?\n\n"
            "## Options Considered\n\n1. \n2. \n\n## Decision\n\n## Consequences\n\n## Links\n\n"
            "- Belongs to: [[COMP-<component>]]\n", encoding="utf-8")
    print(f"  [2/6] Templates ready")

    # Deep scan + bootstrap: detect components, APIs, decisions
    _repo_str = str(repo)
    comp_dir = repo / "components"
    had_comps = set(p.stem for p in comp_dir.glob("*.yaml")) if comp_dir.is_dir() else set()

    # Run bootstrap first (manifest-based)
    class BootArgs:
        repo = _repo_str
        dry_run = False
    cmd_bootstrap(BootArgs())

    # Then run deep scan to find additional components
    scan_skip = {"components", "intent", "interfaces", "gates", "templates", "docs", ".intent"}
    new_comps = 0
    for child in sorted(repo.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name in scan_skip:
            continue
        slug = child.name.lower().replace(" ", "-")
        if slug in had_comps:
            continue
        comp_yaml = comp_dir / f"{slug}.yaml"
        if comp_yaml.exists():
            continue
        # Detect if it's a real component (has code or a manifest)
        has_manifest = any((child / m).exists() for m, _ in _MANIFEST_PATTERNS)
        file_count = sum(1 for _ in child.rglob("*") if _.is_file() and ".git" not in str(_) and "node_modules" not in str(_) and "__pycache__" not in str(_))
        if not has_manifest and file_count <= 2:
            continue
        # Detect language
        lang = None
        for manifest, mlang in _MANIFEST_PATTERNS:
            if (child / manifest).exists():
                lang = mlang
                break
        # Create component YAML
        comp_yaml.write_text(
            f"id: COMP-{slug}\nname: {child.name}\n"
            f"description: Auto-detected component ({lang or 'unknown language'})\n"
            f"paths:\n  - \"{child.name}/**\"\n",
            encoding="utf-8",
        )
        # Create a starter spec for the component
        intent_dir = repo / "intent" / slug / "specs"
        intent_dir.mkdir(parents=True, exist_ok=True)
        spec_path = intent_dir / f"SPEC-0001-{slug}-overview.md"
        if not spec_path.exists():
            spec_path.write_text(
                f"---\nid: SPEC-0001\nstatus: draft\n---\n\n"
                f"# {child.name} Overview\n\n"
                f"## Intent\n\nDescribe what {child.name} does and why it exists.\n\n"
                f"## Goals\n\n- \n\n## Non-goals\n\n- \n\n## Acceptance Criteria\n\n- [ ] \n\n"
                f"## Links\n\n- Belongs to: [[COMP-{slug}]]\n",
                encoding="utf-8",
            )
        new_comps += 1

    all_comps = list(comp_dir.glob("*.yaml")) if comp_dir.is_dir() else []
    if all_comps:
        extra = f" ({new_comps} auto-detected)" if new_comps else ""
        print(f"  [3/6] {len(all_comps)} component(s) bootstrapped{extra}")
    else:
        print(f"  [3/6] No components detected (add YAML to components/)")

    # Generate .gitignore entry if missing
    gitignore = repo / ".gitignore"
    if gitignore.exists():
        gi_text = gitignore.read_text(encoding="utf-8", errors="ignore")
    else:
        gi_text = ""
    if ".intent/index/" not in gi_text:
        with open(gitignore, "a", encoding="utf-8") as f:
            f.write("\n# Sigil generated artifacts\n.intent/index/\n")
        print(f"  [4/6] Added .intent/index/ to .gitignore")
    else:
        print(f"  [4/6] .gitignore configured")

    # Build index
    g = build_graph(repo)
    write_graph_artifacts(repo, g)
    print(f"  [5/6] Graph indexed: {len(g.nodes)} nodes, {len(g.edges)} edges")

    # Run scan to generate scan.json report
    class ScanArgs:
        repo = _repo_str
        dry_run = True  # suppress scan output during init
        output = None
    # Write scan.json silently
    idx_dir = repo / ".intent" / "index"
    idx_dir.mkdir(parents=True, exist_ok=True)
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        class ScanSilent:
            repo = _repo_str
            dry_run = False
            output = str(idx_dir / "scan.json")
        cmd_scan(ScanSilent())

    # Ensure viewer exists — copy from package if needed
    viewer = _ensure_viewer(repo)

    # Open viewer
    if viewer:
        import webbrowser
        import threading
        from http.server import HTTPServer, SimpleHTTPRequestHandler

        port = int(getattr(args, "port", 0) or 8787)

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(repo), **kw)
            def log_message(self, format, *a):
                pass  # suppress logs

        try:
            httpd = HTTPServer(("127.0.0.1", port), Handler)
        except OSError:
            port = 0
            httpd = HTTPServer(("127.0.0.1", port), Handler)
            port = httpd.server_address[1]

        url = f"http://127.0.0.1:{port}/tools/intent_viewer/index.html"
        print(f"  [6/6] Viewer ready")
        print()
        print(f"  Viewer:   {url}")
        print(f"  Palette:  Cmd+K")
        print(f"  New doc:  sigil new spec <component> <title>")
        print(f"  Map:      sigil map")
        print(f"  Suggest:  sigil suggest <filepath>")
        print(f"  Status:   sigil status")
        print()
        print(f"  Press Ctrl+C to stop.")
        print()
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
            httpd.server_close()
    else:
        print(f"  [6/6] Viewer not found. Run from a sigil-enabled repo.")

    return 0


def _run_gate_checks(repo: Path, g: Graph) -> list:
    """Run all gate checks and return a list of gate result dicts.

    Each result: {"id", "summary", "kind", "policy", "passed", "findings": [{"severity", "message"}]}
    """
    import fnmatch as _fnmatch

    gates_dir = repo / "gates"
    if not gates_dir.is_dir():
        return []

    results = []

    for p in sorted(gates_dir.glob("*.yaml")):
        data = load_yaml(p) if yaml else {}
        gid = data.get("id", p.stem)
        status = data.get("status", "inactive")
        if status != "active":
            continue

        enforced_by = data.get("enforced_by", {})
        kind = enforced_by.get("kind", "")
        checks = enforced_by.get("checks", [])
        policy = data.get("policy", {})
        on_fail = policy.get("on_fail", "warn")
        docs = data.get("docs", {})
        summary = docs.get("summary", gid)

        applies_to = data.get("applies_to", [])
        target_nodes = set()
        for item in applies_to:
            if isinstance(item, dict):
                n = item.get("node")
                if n:
                    target_nodes.add(n)
            elif isinstance(item, str):
                target_nodes.add(item)

        # Find all nodes that belong to the target nodes
        governed_nodes = set()
        for nid in target_nodes:
            governed_nodes.add(nid)
            for e in g.edges:
                if e.dst == nid and e.type == "belongs_to":
                    governed_nodes.add(e.src)

        findings: list = []

        if kind == "lint-rule":
            for check in checks:
                if check == "all_specs_have_acceptance_criteria":
                    for nid in governed_nodes:
                        node = g.nodes.get(nid)
                        if node and node.type == "spec":
                            md = read_text(repo / node.path)
                            if "## Acceptance Criteria" not in md:
                                findings.append({"severity": "FAIL", "message": f"{nid}: missing ## Acceptance Criteria"})

                elif check == "all_specs_have_status":
                    for nid in governed_nodes:
                        node = g.nodes.get(nid)
                        if node and node.type == "spec":
                            md = read_text(repo / node.path)
                            fm, _ = parse_front_matter(md)
                            if not fm.get("status"):
                                findings.append({"severity": "FAIL", "message": f"{nid}: missing status in front matter"})

                elif check == "all_adrs_have_status":
                    for nid in governed_nodes:
                        node = g.nodes.get(nid)
                        if node and node.type == "adr":
                            md = read_text(repo / node.path)
                            fm, _ = parse_front_matter(md)
                            if not fm.get("status"):
                                findings.append({"severity": "FAIL", "message": f"{nid}: missing status in front matter"})

                elif check == "no_dangling_references":
                    all_ids = set(g.nodes.keys())
                    for e in g.edges:
                        if e.src in governed_nodes and e.dst not in all_ids:
                            findings.append({"severity": "FAIL", "message": f"{e.src}: dangling ref -> {e.dst}"})

                elif check == "no_draft_adrs_older_than_30_days":
                    for nid in governed_nodes:
                        node = g.nodes.get(nid)
                        if node and node.type == "adr":
                            md = read_text(repo / node.path)
                            fm, _ = parse_front_matter(md)
                            if fm.get("status") in ("draft", "proposed"):
                                findings.append({"severity": "WARN", "message": f"{nid}: still in {fm['status']} status"})

        elif kind == "command":
            cmd = enforced_by.get("command", [])
            workdir = enforced_by.get("workdir", ".")
            if cmd:
                try:
                    result = subprocess.run(cmd, cwd=str(repo / workdir),
                                           capture_output=True, text=True, timeout=30)
                    if result.returncode != 0:
                        stderr_snippet = result.stderr.strip()[:200] if result.stderr else result.stdout.strip()[:200]
                        findings.append({"severity": "FAIL", "message": f"command exited {result.returncode}: {stderr_snippet}"})
                except Exception as ex:
                    findings.append({"severity": "FAIL", "message": f"command error: {ex}"})

        elif kind == "pattern":
            patterns = enforced_by.get("patterns", [])
            for pat_entry in patterns:
                glob_pat = pat_entry.get("glob", "**/*")
                regex_str = pat_entry.get("regex", "")
                negate = pat_entry.get("negate", False)
                label = pat_entry.get("label", regex_str)
                if not regex_str:
                    continue
                try:
                    regex = re.compile(regex_str)
                except re.error as exc:
                    findings.append({"severity": "FAIL", "message": f"invalid regex '{regex_str}': {exc}"})
                    continue
                for fpath in repo.glob(glob_pat):
                    if not fpath.is_file():
                        continue
                    rel = str(fpath.relative_to(repo))
                    if any(rel.startswith(s) for s in [".git/", ".intent/", "__pycache__/"]):
                        continue
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue
                    matches = regex.findall(content)
                    if negate:
                        if not matches:
                            findings.append({"severity": "FAIL", "message": f"{rel}: expected pattern '{label}' not found"})
                    else:
                        if matches:
                            findings.append({"severity": "FAIL", "message": f"{rel}: forbidden pattern '{label}' found ({len(matches)} match(es))"})

        elif kind == "threshold":
            threshold_val = enforced_by.get("threshold", 0)
            metric = enforced_by.get("metric", "intent_coverage")
            if metric == "intent_coverage":
                # Compute intent coverage using component path mappings
                comp_paths: Dict[str, List[str]] = {}
                components_dir = repo / "components"
                if components_dir.is_dir():
                    for cp in components_dir.glob("*.yaml"):
                        cdata = load_yaml(cp) if yaml else {}
                        cid = cdata.get("id") or f"COMP-{cp.stem}"
                        cpaths = cdata.get("paths", [])
                        if isinstance(cpaths, list):
                            comp_paths[cid] = cpaths

                # Get all tracked files
                all_files = []
                try:
                    out = run_cmd(["git", "-C", str(repo), "ls-files", "--cached", "--others", "--exclude-standard"])
                    all_files = [f for f in out.strip().split("\n") if f.strip()]
                except Exception:
                    for f in repo.rglob("*"):
                        if f.is_file() and ".git/" not in str(f):
                            all_files.append(str(f.relative_to(repo)))

                skip_prefixes = [".intent/", ".git/", ".github/", "templates/", "components/", "intent/", "gates/", "interfaces/"]
                code_files = [f for f in all_files if not any(f.startswith(s) for s in skip_prefixes)]
                covered = 0
                for cf in code_files:
                    for cid, pats in comp_paths.items():
                        if any(_fnmatch.fnmatch(cf, pat) for pat in pats):
                            covered += 1
                            break
                coverage_pct = round(covered / max(len(code_files), 1) * 100) if code_files else 100
                if coverage_pct < threshold_val:
                    findings.append({"severity": "FAIL", "message": f"intent coverage {coverage_pct}% < threshold {threshold_val}%"})

        has_fail = any(f["severity"] == "FAIL" for f in findings)
        # Determine final pass/fail based on policy
        if on_fail == "warn" and has_fail:
            # Downgrade FAILs to WARNs when policy is warn
            for f in findings:
                if f["severity"] == "FAIL":
                    f["severity"] = "WARN"
            passed = True
        else:
            passed = not has_fail

        results.append({
            "id": gid,
            "summary": summary,
            "kind": kind,
            "policy": on_fail,
            "passed": passed,
            "scope": len(governed_nodes),
            "findings": findings,
        })

    return results


def cmd_check(args) -> int:
    """Run gate checks against the intent graph."""
    repo = Path(args.repo).resolve()
    g = build_graph(repo)
    gates_dir = repo / "gates"
    if not gates_dir.is_dir():
        print("No gates/ directory found.")
        return 0

    use_json = getattr(args, "json", False)
    results = _run_gate_checks(repo, g)

    if use_json:
        total_pass = sum(1 for r in results if r["passed"])
        total_fail = sum(1 for r in results if not r["passed"])
        print(json.dumps({"gates": results, "passed": total_pass, "failed": total_fail}, indent=2))
        return 1 if total_fail > 0 else 0

    if not results:
        print("No active gates found.")
        return 0

    # Print per-gate details
    for r in results:
        print(f"\n  GATE {r['id']}: {r['summary']}")
        print(f"  kind: {r['kind']}  |  policy: {r['policy']}  |  scope: {r['scope']} node(s)")
        if r["findings"]:
            for f in r["findings"]:
                print(f"    {f['severity']} {f['message']}")
        else:
            print(f"    PASS")

    # Summary table
    total_pass = sum(1 for r in results if r["passed"])
    total_fail = sum(1 for r in results if not r["passed"])
    total_warn = sum(1 for r in results for f in r["findings"] if f["severity"] == "WARN")

    print()
    print("  " + "-" * 52)
    print(f"  {'Gate':<16} {'Kind':<12} {'Policy':<8} {'Result':<8}")
    print("  " + "-" * 52)
    for r in results:
        status_label = "PASS" if r["passed"] else "FAIL"
        print(f"  {r['id']:<16} {r['kind']:<12} {r['policy']:<8} {status_label:<8}")
    print("  " + "-" * 52)
    print(f"\n  Gates: {total_pass} passed, {total_fail} failed, {total_warn} warning(s)")

    # Write gate results to .intent/index/gates.json
    out_dir = repo / ".intent" / "index"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "gates.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    return 1 if total_fail > 0 else 0


def cmd_drift(args) -> int:
    """Detect drift between intent graph and actual codebase."""
    import fnmatch

    repo = Path(args.repo).resolve()
    g = build_graph(repo)

    # Load component path patterns
    comp_paths: Dict[str, List[str]] = {}  # comp_id -> [glob patterns]
    components_dir = repo / "components"
    if components_dir.is_dir():
        for p in components_dir.glob("*.yaml"):
            data = load_yaml(p) if yaml else {}
            cid = data.get("id") or f"COMP-{p.stem}"
            paths = data.get("paths", [])
            if isinstance(paths, list):
                comp_paths[cid] = paths

    # Scan all files (tracked + untracked)
    tracked = []
    try:
        out = run_cmd(["git", "-C", str(repo), "ls-files", "--cached", "--others", "--exclude-standard"])
        tracked = [f for f in out.strip().split("\n") if f.strip()]
    except Exception:
        pass
    if not tracked:
        for f in repo.rglob("*"):
            if f.is_file() and not any(s in str(f) for s in [".git/", "__pycache__", "node_modules", ".intent/"]):
                tracked.append(str(f.relative_to(repo)))

    # Map files to components
    file_to_comp: Dict[str, str] = {}
    unowned: List[str] = []
    skip_prefixes = [".intent/", ".git/", ".github/", "templates/", "components/", "intent/", "gates/", "interfaces/"]

    for fpath in tracked:
        if not fpath.strip():
            continue
        if any(fpath.startswith(sp) for sp in skip_prefixes):
            continue
        matched = False
        for cid, patterns in comp_paths.items():
            for pat in patterns:
                if fnmatch.fnmatch(fpath, pat):
                    file_to_comp[fpath] = cid
                    matched = True
                    break
            if matched:
                break
        if not matched:
            unowned.append(fpath)

    # Check which components have governing specs
    comps_with_spec = set()
    for e in g.edges:
        if e.type == "belongs_to" and e.dst in comp_paths:
            node = g.nodes.get(e.src)
            if node and node.type == "spec":
                comps_with_spec.add(e.dst)

    # Check for stale specs (accepted but component has new files)
    stale_specs: List[str] = []
    for cid, patterns in comp_paths.items():
        comp_files = [f for f, c in file_to_comp.items() if c == cid]
        if not comp_files:
            continue
        if cid not in comps_with_spec:
            stale_specs.append(f"{cid}: {len(comp_files)} code file(s) but no governing spec")

    # Output drift report
    findings: list = []

    print(f"\n  Drift Detection Report")
    print(f"  {'='*40}")
    print(f"  Files scanned: {len(tracked)}")
    print(f"  Files mapped to components: {len(file_to_comp)}")
    print(f"  Unowned files: {len(unowned)}")
    print()

    if unowned:
        print(f"  DRIFT: {len(unowned)} file(s) not mapped to any component")
        for f in sorted(unowned)[:15]:
            print(f"    - {f}")
        if len(unowned) > 15:
            print(f"    ... and {len(unowned) - 15} more")
        findings.append({"type": "unowned_files", "count": len(unowned), "files": sorted(unowned)})
        print()

    if stale_specs:
        print(f"  DRIFT: {len(stale_specs)} component(s) have code but no governing spec")
        for msg in stale_specs:
            print(f"    - {msg}")
        findings.append({"type": "no_spec", "items": stale_specs})
        print()

    # Components with specs but zero code files
    empty_comps = []
    for cid in comp_paths:
        comp_files = [f for f, c in file_to_comp.items() if c == cid]
        if not comp_files and cid in comps_with_spec:
            empty_comps.append(cid)
    if empty_comps:
        print(f"  INFO: {len(empty_comps)} component(s) have specs but no matching code files")
        for cid in empty_comps:
            print(f"    - {cid}")
        findings.append({"type": "spec_no_code", "items": empty_comps})
        print()

    # Summary
    total_drift = len(unowned) + len(stale_specs)
    if total_drift == 0:
        print("  No drift detected. Intent and code are aligned.")
    else:
        print(f"  Total drift signals: {total_drift}")

    # Write drift report
    out_dir = repo / ".intent" / "index"
    out_dir.mkdir(parents=True, exist_ok=True)
    drift_json = {
        "scanned": len(tracked),
        "mapped": len(file_to_comp),
        "unowned": len(unowned),
        "findings": findings,
    }
    (out_dir / "drift.json").write_text(json.dumps(drift_json, indent=2), encoding="utf-8")

    return 1 if total_drift > 0 else 0


def cmd_export(args) -> int:
    """Generate a self-contained HTML snapshot of the intent viewer."""
    repo = Path(args.repo).resolve()

    # Build fresh graph
    g = build_graph(repo)
    write_graph_artifacts(repo, g)

    viewer_path = _find_viewer(repo)
    if not viewer_path:
        print("Viewer not found. Run 'sigil init' first or install sigil-cli via pip.")
        return 1

    graph_path = repo / ".intent" / "index" / "graph.json"
    graph_json = graph_path.read_text(encoding="utf-8")
    viewer_html = viewer_path.read_text(encoding="utf-8")

    # Collect all intent file contents for inline viewing
    file_contents: Dict[str, str] = {}
    for n in g.nodes.values():
        p = repo / n.path
        if p.exists():
            file_contents[n.path] = read_text(p)

    # Load optional artifacts for embedding
    drift_json = "{}"
    drift_path = repo / ".intent" / "index" / "drift.json"
    if drift_path.exists():
        drift_json = drift_path.read_text(encoding="utf-8")

    timeline_json = '{"events":[]}'
    timeline_path = repo / ".intent" / "index" / "timeline.json"
    if timeline_path.exists():
        timeline_json = timeline_path.read_text(encoding="utf-8")

    review_json = "{}"
    review_path = repo / ".intent" / "index" / "review.json"
    if review_path.exists():
        review_json = review_path.read_text(encoding="utf-8")

    coverage_json = "{}"
    coverage_path = repo / ".intent" / "index" / "coverage.json"
    if coverage_path.exists():
        coverage_json = coverage_path.read_text(encoding="utf-8")

    # Build self-contained HTML: inject graph data and file contents
    inject_script = f"""
    <script>
    // Injected by sigil export — no server needed
    window.__SIGIL_GRAPH__ = {graph_json};
    window.__SIGIL_FILES__ = {json.dumps(file_contents)};
    window.__SIGIL_DRIFT__ = {drift_json};
    window.__SIGIL_TIMELINE__ = {timeline_json};
    window.__SIGIL_REVIEW__ = {review_json};
    window.__SIGIL_COVERAGE__ = {coverage_json};

    // Override fetch to serve embedded data
    const _origFetch = window.fetch;
    window.fetch = function(url, opts) {{
      const urlStr = String(url);
      if (urlStr.includes('graph.json')) {{
        return Promise.resolve(new Response(JSON.stringify(window.__SIGIL_GRAPH__), {{status: 200}}));
      }}
      if (urlStr.includes('drift.json')) {{
        return Promise.resolve(new Response(JSON.stringify(window.__SIGIL_DRIFT__), {{status: 200}}));
      }}
      if (urlStr.includes('timeline.json')) {{
        return Promise.resolve(new Response(JSON.stringify(window.__SIGIL_TIMELINE__), {{status: 200}}));
      }}
      if (urlStr.includes('review.json')) {{
        return Promise.resolve(new Response(JSON.stringify(window.__SIGIL_REVIEW__), {{status: 200}}));
      }}
      if (urlStr.includes('coverage.json')) {{
        return Promise.resolve(new Response(JSON.stringify(window.__SIGIL_COVERAGE__), {{status: 200}}));
      }}
      // Check file contents
      for (const [path, content] of Object.entries(window.__SIGIL_FILES__)) {{
        if (urlStr.endsWith(path) || urlStr.includes(path)) {{
          return Promise.resolve(new Response(content, {{status: 200}}));
        }}
      }}
      return _origFetch(url, opts);
    }};
    </script>
    """

    # Insert before the closing </head>
    export_html = viewer_html.replace("</head>", inject_script + "\n</head>")
    # Update title
    export_html = export_html.replace(
        "<title>Sigil",
        f"<title>Sigil Export ({len(g.nodes)} nodes) —"
    )

    out_path = Path(args.output) if args.output else repo / ".intent" / "export.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(export_html, encoding="utf-8")
    print(f"Exported to {out_path}")
    print(f"  {len(g.nodes)} nodes, {len(g.edges)} edges")
    print(f"  {len(file_contents)} file(s) embedded")
    print(f"  Open in any browser — no server needed.")
    return 0


def _compute_coverage(repo: Path, g: Graph) -> Dict:
    """Compute intent coverage metrics. Returns structured coverage report."""
    components = [n for n in g.nodes.values() if n.type == "component"]
    specs = [n for n in g.nodes.values() if n.type == "spec"]
    adrs = [n for n in g.nodes.values() if n.type == "adr"]
    gates = [n for n in g.nodes.values() if n.type == "gate"]

    # Components with a governing spec (via belongs_to edges)
    comps_with_spec = set()
    for e in g.edges:
        if e.type == "belongs_to":
            comps_with_spec.add(e.dst)
    comps_without_spec = [c for c in components if c.id not in comps_with_spec]

    # Specs with acceptance criteria
    specs_with_ac = []
    specs_without_ac = []
    for n in specs:
        try:
            md = read_text(repo / n.path)
        except Exception:
            md = ""
        _, body = parse_front_matter(md)
        has_ac = bool(re.search(r"(?i)acceptance\s+criteria|## acceptance", body))
        if has_ac:
            specs_with_ac.append(n)
        else:
            specs_without_ac.append(n)

    # ADR status breakdown
    adr_statuses: Dict[str, list] = {"accepted": [], "draft": [], "proposed": [], "rejected": [], "unknown": []}
    for n in adrs:
        try:
            md = read_text(repo / n.path)
        except Exception:
            md = ""
        fm, _ = parse_front_matter(md)
        status = fm.get("status", "unknown").lower()
        bucket = status if status in adr_statuses else "unknown"
        adr_statuses[bucket].append(n)
    adrs_with_status = len(adrs) - len(adr_statuses["unknown"])

    # Dangling edges
    node_ids = set(g.nodes.keys())
    dangling = [e for e in g.edges if e.dst not in node_ids]

    # Findings
    findings = []
    if comps_without_spec:
        findings.append({"severity": "warn", "message": f"{len(comps_without_spec)} component(s) have no governing spec",
                         "nodes": [c.id for c in comps_without_spec]})
    if specs_without_ac:
        findings.append({"severity": "info", "message": f"{len(specs_without_ac)} spec(s) missing acceptance criteria",
                         "nodes": [s.id for s in specs_without_ac]})
    if adr_statuses["draft"] or adr_statuses["proposed"]:
        draft_nodes = adr_statuses["draft"] + adr_statuses["proposed"]
        findings.append({"severity": "info", "message": f"{len(draft_nodes)} ADR(s) still in draft/proposed",
                         "nodes": [n.id for n in draft_nodes]})
    if dangling:
        findings.append({"severity": "warn", "message": f"{len(dangling)} dangling reference(s) to missing nodes",
                         "nodes": []})

    # Per-component detail
    # Build lookup: which specs belong to which component
    comp_specs: Dict[str, List[str]] = {}
    for e in g.edges:
        if e.type == "belongs_to":
            comp_specs.setdefault(e.dst, []).append(e.src)

    # Build lookup: which ADRs are linked to specs (via decided_by)
    spec_adrs: Dict[str, List[str]] = {}
    for e in g.edges:
        if e.type == "decided_by":
            src_node = g.nodes.get(e.src)
            dst_node = g.nodes.get(e.dst)
            if src_node and dst_node:
                # ADR --decided_by--> SPEC or SPEC --decided_by--> ADR
                if src_node.type == "adr" and dst_node.type == "spec":
                    spec_adrs.setdefault(e.dst, []).append(e.src)
                elif src_node.type == "spec" and dst_node.type == "adr":
                    spec_adrs.setdefault(e.src, []).append(e.dst)

    comp_details = []
    for c in components:
        has_spec = c.id in comps_with_spec
        my_specs = comp_specs.get(c.id, [])
        adr_ids = set()
        for sid in my_specs:
            adr_ids.update(spec_adrs.get(sid, []))
        comp_gates = [e.dst for e in g.edges if e.type == "gated_by" and e.src == c.id]
        level = "green" if has_spec and adr_ids else ("yellow" if has_spec or adr_ids else "red")
        comp_details.append({"id": c.id, "title": c.title, "has_spec": has_spec,
                             "adr_count": len(adr_ids), "gate_count": len(comp_gates), "level": level})

    # Weighted score (matches viewer logic)
    score = 0.0
    max_score = 0.0

    # Component coverage (40%)
    if components:
        score += (len(comps_with_spec) / len(components)) * 40
        max_score += 40

    # ADR maturity (30%)
    if adrs:
        score += (len(adr_statuses["accepted"]) / len(adrs)) * 30
        max_score += 30

    # Spec quality — acceptance criteria (20%)
    if specs:
        score += (len(specs_with_ac) / len(specs)) * 20
        max_score += 20

    # No dangling refs (10%)
    if g.edges:
        clean = len(g.edges) - len(dangling)
        score += (clean / len(g.edges)) * 10
        max_score += 10

    pct = round((score / max_score) * 100) if max_score else 0

    return {
        "score": pct,
        "metrics": {
            "components_with_spec": {"value": len(comps_with_spec), "total": len(components),
                                     "pct": round(len(comps_with_spec) / len(components) * 100) if components else 0},
            "specs_with_acceptance": {"value": len(specs_with_ac), "total": len(specs),
                                     "pct": round(len(specs_with_ac) / len(specs) * 100) if specs else 0},
            "adrs_with_status": {"value": adrs_with_status, "total": len(adrs),
                                 "pct": round(adrs_with_status / len(adrs) * 100) if adrs else 0},
            "adrs_accepted": {"value": len(adr_statuses["accepted"]), "total": len(adrs),
                              "pct": round(len(adr_statuses["accepted"]) / len(adrs) * 100) if adrs else 0},
        },
        "stats": {"nodes": len(g.nodes), "edges": len(g.edges), "components": len(components),
                  "specs": len(specs), "adrs": len(adrs), "gates": len(gates)},
        "components": comp_details,
        "findings": findings,
    }


def _coverage_color(pct: int) -> str:
    if pct >= 80:
        return "#04b372"
    elif pct >= 60:
        return "#458ae2"
    elif pct >= 40:
        return "#f2a633"
    return "#e7349c"


def _coverage_label(pct: int) -> str:
    if pct >= 80:
        return "excellent"
    elif pct >= 60:
        return "good"
    elif pct >= 40:
        return "fair"
    return "needs work"


def cmd_coverage(args) -> int:
    """Output intent coverage report."""
    repo = Path(args.repo).resolve()
    g = build_graph(repo)
    cov = _compute_coverage(repo, g)

    if getattr(args, "json", False):
        print(json.dumps(cov, indent=2))
    else:
        pct = cov["score"]
        label = _coverage_label(pct)
        s = cov["stats"]
        m = cov["metrics"]

        print(f"\n  Intent Coverage: {pct}% ({label})")
        print(f"  {'=' * 40}")
        print(f"  Graph: {s['nodes']} nodes, {s['edges']} edges\n")
        print(f"  Components with spec:    {m['components_with_spec']['value']}/{m['components_with_spec']['total']} ({m['components_with_spec']['pct']}%)")
        print(f"  Specs with acceptance:   {m['specs_with_acceptance']['value']}/{m['specs_with_acceptance']['total']} ({m['specs_with_acceptance']['pct']}%)")
        print(f"  ADRs with status:        {m['adrs_with_status']['value']}/{m['adrs_with_status']['total']} ({m['adrs_with_status']['pct']}%)")
        print(f"  ADRs accepted:           {m['adrs_accepted']['value']}/{m['adrs_accepted']['total']} ({m['adrs_accepted']['pct']}%)")

        if cov["components"]:
            print(f"\n  Components:")
            for c in cov["components"]:
                icon = {"green": "+", "yellow": "~", "red": "-"}[c["level"]]
                spec_mark = "spec" if c["has_spec"] else "no spec"
                print(f"    [{icon}] {c['id']}: {spec_mark}, {c['adr_count']} ADR(s), {c['gate_count']} gate(s)")

        if cov["findings"]:
            print(f"\n  Findings:")
            for f in cov["findings"]:
                icon = "!" if f["severity"] == "warn" else "i"
                print(f"    [{icon}] {f['message']}")

        print()

    # Write coverage.json
    out_dir = repo / ".intent" / "index"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "coverage.json").write_text(json.dumps(cov, indent=2), encoding="utf-8")

    return 0


def cmd_badge(args) -> int:
    """Generate an intent coverage badge SVG."""
    repo = Path(args.repo).resolve()
    g = build_graph(repo)
    cov = _compute_coverage(repo, g)
    pct = cov["score"]
    color = _coverage_color(pct)

    label = "intent coverage"
    value = f"{pct}%"
    label_width = len(label) * 6.5 + 12
    value_width = len(value) * 7 + 12
    total_width = label_width + value_width

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" role="img" aria-label="{label}: {value}">
  <linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
  <clipPath id="r"><rect width="{total_width}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="20" fill="#1a1c22"/>
    <rect x="{label_width}" width="{value_width}" height="20" fill="{color}"/>
    <rect width="{total_width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{label_width/2}" y="14" fill="#dbd6cc">{label}</text>
    <text x="{label_width + value_width/2}" y="14" font-weight="bold">{value}</text>
  </g>
</svg>"""

    out_path = Path(args.output) if args.output else repo / ".intent" / "badge.svg"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")
    print(f"Badge: {out_path}")
    print(f"  Score: {pct}% ({len(g.nodes)} nodes, {len(g.edges)} edges)")
    return 0


def cmd_serve(args) -> int:
    """Start a dev server with file watching. Rebuilds graph on changes."""
    import webbrowser
    import threading
    import time
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    repo = Path(args.repo).resolve()
    port = int(args.port)

    # Initial build
    g = build_graph(repo)
    write_graph_artifacts(repo, g)
    print(f"Indexed {len(g.nodes)} nodes, {len(g.edges)} edges")

    # Live reload version counter
    rebuild_version = [1]

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
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(json.dumps({"version": rebuild_version[0]}).encode())
                return
            return super().do_GET()
        def do_POST(self):
            if self.path == "/api/new":
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}
                node_type = body.get("type", "spec")
                component = body.get("component", "")
                title = body.get("title", "Untitled")
                if not component:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "component required"}).encode())
                    return
                # Create new doc using same logic as cmd_new
                templates_dir = repo / "templates"
                config_path = repo / ".intent" / "config.yaml"
                next_num = 1
                if config_path.exists() and yaml:
                    cfg = load_yaml(config_path)
                    counters = cfg.get("id_counters", {})
                    prefix = node_type.upper()
                    next_num = counters.get(prefix, 0) + 1
                type_to_template = {"spec": "SPEC.md", "adr": "ADR.md"}
                template_file = type_to_template.get(node_type)
                if not template_file:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"unknown type: {node_type}"}).encode())
                    return
                template_path = templates_dir / template_file
                if not template_path.exists():
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "template not found"}).encode())
                    return
                prefix = node_type.upper()
                node_id = f"{prefix}-{next_num:04d}"
                slug = title.lower().replace(" ", "-").replace("/", "-")
                filename = f"{node_id}-{slug}.md"
                subdir_map = {"spec": "specs", "adr": "adrs"}
                subdir = subdir_map.get(node_type, node_type + "s")
                dest_dir = repo / "intent" / component / subdir
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / filename
                content = read_text(template_path)
                content = content.replace(f"{prefix}-0000", node_id)
                content = content.replace("<Title>", title)
                content = content.replace("<Decision>", title)
                content = content.replace("<component>", component)
                dest.write_text(content, encoding="utf-8")
                # Rebuild graph
                g2 = build_graph(repo)
                write_graph_artifacts(repo, g2)
                print(f"  created: {node_id} ({dest.relative_to(repo)})")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "id": node_id, "type": node_type, "title": title,
                    "path": str(dest.relative_to(repo)).replace("\\", "/"),
                    "nodes": len(g2.nodes), "edges": len(g2.edges)
                }).encode())
                return
            self.send_response(404)
            self.end_headers()
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

    try:
        httpd = HTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        httpd = HTTPServer(("127.0.0.1", 0), Handler)
        port = httpd.server_address[1]

    url = f"http://127.0.0.1:{port}/tools/intent_viewer/index.html"

    # File watcher: poll for changes every 2 seconds
    watch_dirs = ["components", "intent", "interfaces", "gates"]
    last_mtimes: Dict[str, float] = {}

    def scan_mtimes() -> Dict[str, float]:
        mtimes: Dict[str, float] = {}
        for wd in watch_dirs:
            d = repo / wd
            if not d.is_dir():
                continue
            for f in d.rglob("*"):
                if f.is_file():
                    try:
                        mtimes[str(f)] = f.stat().st_mtime
                    except OSError:
                        pass
        return mtimes

    last_mtimes = scan_mtimes()

    def watcher():
        nonlocal last_mtimes
        while True:
            time.sleep(2)
            current = scan_mtimes()
            if current != last_mtimes:
                changed = set(current.keys()) ^ set(last_mtimes.keys())
                modified = {k for k in current if k in last_mtimes and current[k] != last_mtimes[k]}
                changed.update(modified)
                last_mtimes = current
                try:
                    g2 = build_graph(repo)
                    write_graph_artifacts(repo, g2)
                    rebuild_version[0] += 1
                    n_changed = len(changed)
                    print(f"  rebuilt: {len(g2.nodes)} nodes, {len(g2.edges)} edges ({n_changed} file(s) changed) [v{rebuild_version[0]}]")
                except Exception as ex:
                    print(f"  rebuild error: {ex}")

    t = threading.Thread(target=watcher, daemon=True)
    t.start()

    print(f"\n  Sigil dev server")
    print(f"  Viewer: {url}")
    print(f"  Watching: {', '.join(watch_dirs)}")
    print(f"  Live reload: enabled (viewer auto-updates on changes)")
    print(f"  Press Ctrl+C to stop.\n")

    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        httpd.server_close()
    return 0


def cmd_suggest(args) -> int:
    """Given a file path, show which intent docs govern it."""
    import fnmatch as fnm

    repo = Path(args.repo).resolve()
    target = args.path
    g = build_graph(repo)

    # Resolve relative path
    target_path = Path(target)
    if target_path.is_absolute():
        try:
            target_path = target_path.relative_to(repo)
        except ValueError:
            pass
    target_str = str(target_path).replace("\\", "/")

    # 1. Find which component owns this file via path globs
    owning_components: List[str] = []
    comp_dir = repo / "components"
    if comp_dir.is_dir():
        for p in comp_dir.glob("*.yaml"):
            data = load_yaml(p) if yaml else {}
            cid = data.get("id") or f"COMP-{p.stem}"
            paths = data.get("paths", [])
            for pattern in paths:
                if fnm.fnmatch(target_str, pattern):
                    owning_components.append(cid)
                    break

    if not owning_components:
        print(f"  File: {target_str}")
        print(f"  No component owns this file.")
        print(f"  Consider adding a path pattern to a component YAML.")
        return 0

    # 2. Find all intent docs connected to those components
    print(f"\n  File: {target_str}")
    print(f"  {'=' * 40}")

    for comp_id in owning_components:
        comp = g.nodes.get(comp_id)
        if not comp:
            continue
        print(f"\n  Component: {comp.title} ({comp_id})")

        # Find all nodes that belong to this component
        related_specs: List[str] = []
        related_adrs: List[str] = []
        related_gates: List[str] = []
        related_interfaces: List[str] = []

        for e in g.edges:
            if e.dst == comp_id and e.type == "belongs_to":
                node = g.nodes.get(e.src)
                if node:
                    if node.type == "spec":
                        related_specs.append(e.src)
                    elif node.type == "adr":
                        related_adrs.append(e.src)
                    elif node.type == "gate":
                        related_gates.append(e.src)
            if e.src == comp_id and e.type == "gated_by":
                related_gates.append(e.dst)
            if e.dst == comp_id and e.type == "gated_by":
                related_gates.append(e.src)

        # Also check interfaces
        for e in g.edges:
            if (e.src == comp_id or e.dst == comp_id) and e.type in ("provides", "consumes"):
                target_id = e.dst if e.src == comp_id else e.src
                if target_id in g.nodes and g.nodes[target_id].type == "interface":
                    related_interfaces.append(target_id)

        if related_specs:
            print(f"\n  Governing Specs:")
            for sid in sorted(set(related_specs)):
                node = g.nodes[sid]
                fm_raw = read_text(repo / node.path)
                fm, _ = parse_front_matter(fm_raw)
                status = fm.get("status", "?")
                print(f"    [{status}] {sid}: {node.title}")
                print(f"           {node.path}")

        if related_adrs:
            print(f"\n  Relevant ADRs:")
            for aid in sorted(set(related_adrs)):
                node = g.nodes[aid]
                fm_raw = read_text(repo / node.path)
                fm, _ = parse_front_matter(fm_raw)
                status = fm.get("status", "?")
                print(f"    [{status}] {aid}: {node.title}")

        if related_gates:
            print(f"\n  Enforced Gates:")
            for gid in sorted(set(related_gates)):
                node = g.nodes.get(gid)
                if node:
                    print(f"    {gid}: {node.title}")

        if related_interfaces:
            print(f"\n  Interfaces:")
            for iid in sorted(set(related_interfaces)):
                node = g.nodes.get(iid)
                if node:
                    print(f"    {iid}: {node.title}")

    print()
    return 0


def cmd_timeline(args) -> int:
    """Build a timeline of intent evolution from git history."""
    repo = Path(args.repo).resolve()
    max_commits = int(getattr(args, "max", 50))
    out_path = Path(args.output) if args.output else repo / ".intent" / "index" / "timeline.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Get git log for intent-relevant files
    intent_paths = ["components/", "intent/", "interfaces/", "gates/"]
    events: List[dict] = []

    try:
        log_output = run_cmd(
            ["git", "-C", str(repo), "log", "--pretty=format:%H|%aI|%s",
             "--diff-filter=ACDMR", "--name-status", f"-{max_commits}", "--"]
            + intent_paths,
            cwd=repo
        )
    except Exception:
        # No git history — fall back to file timestamps
        g = build_graph(repo)
        now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for nid, node in g.nodes.items():
            p = repo / node.path
            try:
                mtime = dt.datetime.fromtimestamp(p.stat().st_mtime, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                mtime = now
            events.append({
                "date": mtime,
                "sha": "working-tree",
                "message": "current state",
                "action": "added",
                "node_id": nid,
                "node_type": node.type,
                "node_title": node.title,
                "path": node.path,
            })
        events.sort(key=lambda e: e["date"])
        timeline = {"events": events, "generated_at": now}
        out_path.write_text(json.dumps(timeline, indent=2), encoding="utf-8")
        print(f"Timeline: {out_path}")
        print(f"  {len(events)} events (from file timestamps, no git history)")
        return 0

    # Parse git log
    commits: List[dict] = []
    current_commit = None

    for line in log_output.strip().splitlines():
        if not line.strip():
            continue
        if "|" in line and not line.startswith(("A\t", "M\t", "D\t", "R\t", "C\t")):
            parts = line.split("|", 2)
            if len(parts) >= 3:
                current_commit = {"sha": parts[0], "date": parts[1], "message": parts[2], "files": []}
                commits.append(current_commit)
        elif current_commit and "\t" in line:
            status_file = line.split("\t", 1)
            if len(status_file) == 2:
                action = {"A": "added", "M": "modified", "D": "removed"}.get(status_file[0][0], "modified")
                current_commit["files"].append({"action": action, "path": status_file[1]})

    # Build node ID mapping by checking out each commit's graph
    # For efficiency, just map file paths to node IDs using current graph knowledge
    g = build_graph(repo)
    path_to_node: Dict[str, Tuple[str, str, str]] = {}  # path -> (id, type, title)
    for nid, node in g.nodes.items():
        path_to_node[node.path] = (nid, node.type, node.title)

    for commit in commits:
        for f in commit["files"]:
            fpath = f["path"]
            node_info = path_to_node.get(fpath)
            if node_info:
                nid, ntype, ntitle = node_info
            else:
                # Try to infer from filename
                nid = fpath.split("/")[-1].replace(".yaml", "").replace(".md", "").upper()
                ntype = "unknown"
                ntitle = nid
                # Classify from path
                if "components/" in fpath:
                    ntype = "component"
                elif "specs/" in fpath:
                    ntype = "spec"
                elif "adrs/" in fpath:
                    ntype = "adr"
                elif "gates/" in fpath:
                    ntype = "gate"
                elif "interfaces/" in fpath:
                    ntype = "interface"

            events.append({
                "date": commit["date"],
                "sha": commit["sha"][:8],
                "message": commit["message"],
                "action": f["action"],
                "node_id": nid,
                "node_type": ntype,
                "node_title": ntitle,
                "path": fpath,
            })

    events.sort(key=lambda e: e["date"])
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    timeline = {"events": events, "generated_at": now}
    out_path.write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    print(f"Timeline: {out_path}")
    print(f"  {len(events)} events across {len(commits)} commits")
    return 0


def cmd_review(args) -> int:
    """Analyze a git diff and show intent coverage for changed files."""
    import fnmatch as fnm

    repo = Path(args.repo).resolve()
    base = getattr(args, "base", None)
    head_ref = getattr(args, "head", None) or "HEAD"
    staged = getattr(args, "staged", False)
    output_json = getattr(args, "json", False)

    g = build_graph(repo)

    # Load component path patterns
    comp_paths: Dict[str, List[str]] = {}
    comp_dir = repo / "components"
    if comp_dir.is_dir():
        for p in comp_dir.glob("*.yaml"):
            data = load_yaml(p) if yaml else {}
            cid = data.get("id") or f"COMP-{p.stem}"
            paths = data.get("paths", [])
            if isinstance(paths, list):
                comp_paths[cid] = paths

    # Get changed files from git
    try:
        if staged:
            diff_out = run_cmd(["git", "-C", str(repo), "diff", "--cached", "--name-status"], cwd=repo)
        elif base:
            diff_out = run_cmd(["git", "-C", str(repo), "diff", "--name-status", base, head_ref], cwd=repo)
        else:
            diff_out = run_cmd(["git", "-C", str(repo), "diff", "--name-status", "HEAD"], cwd=repo)
            # Also pick up untracked files
            try:
                untracked = run_cmd(
                    ["git", "-C", str(repo), "ls-files", "--others", "--exclude-standard"],
                    cwd=repo,
                )
                for f in untracked.strip().split("\n"):
                    if f.strip():
                        diff_out += f"A\t{f.strip()}\n"
            except Exception:
                pass
    except Exception:
        # Fallback: treat all files as changed (no git history)
        diff_out = ""
        for f in repo.rglob("*"):
            if f.is_file() and not any(s in str(f) for s in [".git/", "__pycache__", "node_modules", ".intent/index"]):
                rel = str(f.relative_to(repo))
                diff_out += f"A\t{rel}\n"

    # Parse diff output
    changes: List[Tuple[str, str]] = []  # (status, path)
    for line in diff_out.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            status_code = parts[0].strip()[0] if parts[0].strip() else "M"
            fpath = parts[1].strip()
            changes.append((status_code, fpath))

    if not changes:
        print("\n  No changes to review.")
        return 0

    # Classify changes
    skip_prefixes = [".intent/index/", ".git/", "templates/", ".pytest_cache/"]
    intent_prefixes = ["components/", "intent/", "interfaces/", "gates/"]

    intent_changes: List[Tuple[str, str]] = []
    code_changes: List[Tuple[str, str]] = []

    for status, fpath in changes:
        if any(fpath.startswith(sp) for sp in skip_prefixes):
            continue
        if any(fpath.startswith(ip) for ip in intent_prefixes):
            intent_changes.append((status, fpath))
        else:
            code_changes.append((status, fpath))

    # Map code files to components
    covered: Dict[str, List[Tuple[str, str]]] = {}  # comp_id -> [(status, path)]
    uncovered: List[Tuple[str, str]] = []

    for status, fpath in code_changes:
        matched = False
        for cid, patterns in comp_paths.items():
            for pat in patterns:
                if fnm.fnmatch(fpath, pat):
                    covered.setdefault(cid, []).append((status, fpath))
                    matched = True
                    break
            if matched:
                break
        if not matched:
            uncovered.append((status, fpath))

    # Build review report
    status_labels = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}

    # Collect component-level governance info
    comp_governance: Dict[str, dict] = {}
    for cid in covered:
        specs = []
        adrs = []
        gates = []
        for e in g.edges:
            if e.dst == cid and e.type == "belongs_to":
                node = g.nodes.get(e.src)
                if node:
                    if node.type == "spec":
                        fm_raw = read_text(repo / node.path)
                        fm, _ = parse_front_matter(fm_raw)
                        specs.append({"id": e.src, "title": node.title, "status": fm.get("status", "?")})
                    elif node.type == "adr":
                        fm_raw = read_text(repo / node.path)
                        fm, _ = parse_front_matter(fm_raw)
                        adrs.append({"id": e.src, "title": node.title, "status": fm.get("status", "?")})
            if e.type == "gated_by" and (e.src == cid or e.dst == cid):
                gid = e.dst if e.src == cid else e.src
                gnode = g.nodes.get(gid)
                if gnode:
                    gates.append({"id": gid, "title": gnode.title})
        # Deduplicate
        seen_ids = set()
        specs = [s for s in specs if s["id"] not in seen_ids and not seen_ids.add(s["id"])]
        seen_ids.clear()
        adrs = [a for a in adrs if a["id"] not in seen_ids and not seen_ids.add(a["id"])]
        seen_ids.clear()
        gates = [g for g in gates if g["id"] not in seen_ids and not seen_ids.add(g["id"])]
        comp_governance[cid] = {"specs": specs, "adrs": adrs, "gates": gates}

    # JSON output
    if output_json:
        report = {
            "summary": {
                "total_changes": len(changes),
                "intent_changes": len(intent_changes),
                "code_changes": len(code_changes),
                "covered_files": sum(len(v) for v in covered.values()),
                "uncovered_files": len(uncovered),
                "coverage_pct": round(
                    sum(len(v) for v in covered.values()) / max(len(code_changes), 1) * 100
                ),
            },
            "intent_changes": [{"status": s, "path": p} for s, p in intent_changes],
            "covered": {
                cid: {
                    "files": [{"status": s, "path": p} for s, p in files],
                    "governance": comp_governance.get(cid, {}),
                }
                for cid, files in covered.items()
            },
            "uncovered": [{"status": s, "path": p} for s, p in uncovered],
        }
        print(json.dumps(report, indent=2))
        return 0

    # Terminal output
    total_code = len(code_changes)
    covered_count = sum(len(v) for v in covered.values())
    coverage_pct = round(covered_count / max(total_code, 1) * 100)

    # Coverage color
    if coverage_pct >= 80:
        cov_label = "GOOD"
    elif coverage_pct >= 50:
        cov_label = "FAIR"
    else:
        cov_label = "LOW"

    print(f"\n  Sigil Review")
    print(f"  {'=' * 50}")
    print(f"  {len(changes)} file(s) changed  |  intent coverage: {coverage_pct}% ({cov_label})")
    print()

    if intent_changes:
        print(f"  Intent Documents Changed ({len(intent_changes)}):")
        for status, fpath in intent_changes:
            label = status_labels.get(status, status)
            print(f"    [{label}] {fpath}")
        print()

    if covered:
        print(f"  Governed Code Changes ({covered_count} files):")
        for cid, files in sorted(covered.items()):
            comp = g.nodes.get(cid)
            comp_name = comp.title if comp else cid
            gov = comp_governance.get(cid, {})
            print(f"\n    {comp_name} ({cid})")
            for status, fpath in files:
                label = status_labels.get(status, status)
                print(f"      [{label}] {fpath}")
            if gov.get("specs"):
                print(f"      Specs: {', '.join(s['id'] + ' [' + s['status'] + ']' for s in gov['specs'])}")
            if gov.get("adrs"):
                print(f"      ADRs:  {', '.join(a['id'] + ' [' + a['status'] + ']' for a in gov['adrs'])}")
            if gov.get("gates"):
                print(f"      Gates: {', '.join(g['id'] for g in gov['gates'])}")
        print()

    if uncovered:
        print(f"  Ungoverned Changes ({len(uncovered)} files):")
        for status, fpath in uncovered:
            label = status_labels.get(status, status)
            print(f"    [{label}] {fpath}")
        print(f"\n  These files are not mapped to any component.")
        print(f"  Run 'sigil suggest <path>' for governance recommendations.")
        print()

    # Warnings
    warnings = []
    for cid, gov in comp_governance.items():
        if not gov.get("specs"):
            comp = g.nodes.get(cid)
            comp_name = comp.title if comp else cid
            warnings.append(f"{comp_name}: code changes but no governing spec")
        draft_specs = [s for s in gov.get("specs", []) if s["status"] == "draft"]
        if draft_specs:
            for s in draft_specs:
                warnings.append(f"{s['id']} ({s['title']}): still in draft — consider promoting before merge")

    if warnings:
        print(f"  Warnings:")
        for w in warnings:
            print(f"    - {w}")
        print()

    return 0


_HOOK_SCRIPT = """\
#!/bin/sh
# Sigil intent coverage check — installed by `sigil hook install`
# Runs `sigil review --staged` on every commit to flag ungoverned changes.

echo ""
echo "  Sigil: checking intent coverage..."
echo ""

sigil_cmd=""
if command -v sigil >/dev/null 2>&1; then
    sigil_cmd="sigil"
elif command -v python3 >/dev/null 2>&1; then
    # Find sigil.py relative to repo root
    repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"
    if [ -f "$repo_root/tools/intent/sigil.py" ]; then
        sigil_cmd="python3 $repo_root/tools/intent/sigil.py"
    fi
fi

if [ -z "$sigil_cmd" ]; then
    echo "  Sigil: not found, skipping review."
    exit 0
fi

$sigil_cmd review --staged

# Non-blocking: always allow commit, just inform
exit 0
"""


def cmd_hook(args) -> int:
    """Install or uninstall the Sigil git pre-commit hook."""
    repo = Path(args.repo).resolve()
    action = args.action
    hook_dir = repo / ".git" / "hooks"
    hook_path = hook_dir / "pre-commit"
    sigil_marker = "# Sigil intent coverage check"

    if action == "install":
        if not hook_dir.is_dir():
            print(f"  Not a git repository (no .git/hooks at {hook_dir})")
            return 1

        if hook_path.exists():
            existing = hook_path.read_text()
            if sigil_marker in existing:
                print(f"  Sigil hook already installed at {hook_path}")
                return 0
            # Append to existing hook
            with open(hook_path, "a") as f:
                f.write("\n\n" + _HOOK_SCRIPT)
            print(f"  Appended Sigil hook to existing {hook_path}")
        else:
            hook_path.write_text(_HOOK_SCRIPT)
            hook_path.chmod(0o755)
            print(f"  Installed Sigil pre-commit hook at {hook_path}")

        print(f"  Every commit will now show intent coverage for staged files.")
        return 0

    elif action == "uninstall":
        if not hook_path.exists():
            print(f"  No pre-commit hook found at {hook_path}")
            return 0

        content = hook_path.read_text()
        if sigil_marker not in content:
            print(f"  Sigil hook not found in {hook_path}")
            return 0

        # Remove the sigil hook section
        lines = content.split("\n")
        new_lines = []
        skip = False
        for line in lines:
            if sigil_marker in line:
                skip = True
                # Also remove blank lines before the marker
                while new_lines and not new_lines[-1].strip():
                    new_lines.pop()
                continue
            if skip and line.startswith("exit 0"):
                skip = False
                continue
            if skip:
                continue
            new_lines.append(line)

        remaining = "\n".join(new_lines).strip()
        if not remaining or remaining == "#!/bin/sh":
            hook_path.unlink()
            print(f"  Removed Sigil pre-commit hook ({hook_path})")
        else:
            hook_path.write_text(remaining + "\n")
            print(f"  Removed Sigil section from {hook_path}")
        return 0

    elif action == "status":
        if hook_path.exists() and sigil_marker in hook_path.read_text():
            print(f"  Sigil pre-commit hook: installed")
        else:
            print(f"  Sigil pre-commit hook: not installed")
            print(f"  Run 'sigil hook install' to enable intent review on commit.")
        return 0

    return 1


def cmd_pr(args) -> int:
    """Analyze a GitHub PR for intent coverage and post a comment."""
    import fnmatch as fnm

    repo = Path(args.repo).resolve()
    pr_num = getattr(args, "number", None)
    dry_run = getattr(args, "dry_run", False)

    # Detect PR context via gh CLI
    try:
        if pr_num:
            pr_json = run_cmd(["gh", "pr", "view", str(pr_num), "--json",
                               "number,title,headRefName,baseRefName,url,additions,deletions,changedFiles"],
                              cwd=repo)
        else:
            pr_json = run_cmd(["gh", "pr", "view", "--json",
                               "number,title,headRefName,baseRefName,url,additions,deletions,changedFiles"],
                              cwd=repo)
    except Exception as ex:
        print(f"  Error: could not detect PR. Are you on a PR branch?\n  {ex}")
        print(f"  Usage: sigil pr [number]  (or run from a branch with an open PR)")
        return 1

    pr = json.loads(pr_json)
    pr_number = pr["number"]
    pr_title = pr["title"]
    base_ref = pr["baseRefName"]
    head_ref = pr["headRefName"]
    pr_url = pr["url"]

    print(f"\n  Sigil PR Analysis")
    print(f"  {'=' * 50}")
    print(f"  PR #{pr_number}: {pr_title}")
    print(f"  {base_ref} <- {head_ref}")
    print()

    # Build graph from current working tree
    g = build_graph(repo)

    # Get diff files from the PR
    try:
        diff_files = run_cmd(["gh", "pr", "diff", str(pr_number), "--name-only"], cwd=repo)
    except Exception:
        diff_files = run_cmd(["git", "-C", str(repo), "diff", "--name-only",
                              f"origin/{base_ref}...HEAD"], cwd=repo)

    # Load component path patterns
    comp_paths: Dict[str, List[str]] = {}
    comp_dir = repo / "components"
    if comp_dir.is_dir():
        for p in comp_dir.glob("*.yaml"):
            data = load_yaml(p) if yaml else {}
            cid = data.get("id") or f"COMP-{p.stem}"
            paths = data.get("paths", [])
            if isinstance(paths, list):
                comp_paths[cid] = paths

    # Classify files
    skip_prefixes = [".intent/index/", ".git/", "templates/", ".pytest_cache/"]
    intent_prefixes = ["components/", "intent/", "interfaces/", "gates/"]

    intent_changes = []
    code_changes = []

    for line in diff_files.strip().split("\n"):
        fpath = line.strip()
        if not fpath:
            continue
        if any(fpath.startswith(sp) for sp in skip_prefixes):
            continue
        if any(fpath.startswith(ip) for ip in intent_prefixes):
            intent_changes.append(fpath)
        else:
            code_changes.append(fpath)

    # Map code files to components
    covered: Dict[str, List[str]] = {}
    uncovered: List[str] = []

    for fpath in code_changes:
        matched = False
        for cid, patterns in comp_paths.items():
            for pat in patterns:
                if fnm.fnmatch(fpath, pat):
                    covered.setdefault(cid, []).append(fpath)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            uncovered.append(fpath)

    # Component governance info
    comp_governance: Dict[str, dict] = {}
    for cid in covered:
        specs = []
        adrs = []
        gates_list = []
        for e in g.edges:
            if e.dst == cid and e.type == "belongs_to":
                node = g.nodes.get(e.src)
                if node:
                    if node.type == "spec":
                        fm_raw = read_text(repo / node.path)
                        fm, _ = parse_front_matter(fm_raw)
                        specs.append({"id": e.src, "title": node.title, "status": fm.get("status", "?")})
                    elif node.type == "adr":
                        fm_raw = read_text(repo / node.path)
                        fm, _ = parse_front_matter(fm_raw)
                        adrs.append({"id": e.src, "title": node.title, "status": fm.get("status", "?")})
            if e.type == "gated_by" and (e.src == cid or e.dst == cid):
                gid = e.dst if e.src == cid else e.src
                gnode = g.nodes.get(gid)
                if gnode:
                    gates_list.append({"id": gid, "title": gnode.title})
        seen = set()
        specs = [s for s in specs if s["id"] not in seen and not seen.add(s["id"])]
        seen.clear()
        adrs = [a for a in adrs if a["id"] not in seen and not seen.add(a["id"])]
        seen.clear()
        gates_list = [gl for gl in gates_list if gl["id"] not in seen and not seen.add(gl["id"])]
        comp_governance[cid] = {"specs": specs, "adrs": adrs, "gates": gates_list}

    # Run gate checks
    gate_results = _run_gate_checks(repo, g)

    # Compute stats
    total_code = len(code_changes)
    covered_count = sum(len(v) for v in covered.values())
    coverage_pct = round(covered_count / max(total_code, 1) * 100) if total_code > 0 else 100

    # Build markdown comment
    if coverage_pct >= 80:
        cov_emoji = "🟢"
    elif coverage_pct >= 50:
        cov_emoji = "🟡"
    else:
        cov_emoji = "🔴"

    all_gates_pass = all(gr["passed"] for gr in gate_results)
    gate_emoji = "🟢" if all_gates_pass else "🔴"

    md_lines = []
    md_lines.append("## Sigil Intent Analysis")
    md_lines.append("")
    md_lines.append(f"| Metric | Value |")
    md_lines.append(f"|--------|-------|")
    md_lines.append(f"| Intent Coverage | {cov_emoji} **{coverage_pct}%** ({covered_count}/{total_code} files) |")
    md_lines.append(f"| Intent Docs Changed | {len(intent_changes)} |")
    md_lines.append(f"| Graph Nodes | {len(g.nodes)} |")
    md_lines.append(f"| Graph Edges | {len(g.edges)} |")
    md_lines.append(f"| Gates | {gate_emoji} {sum(1 for gr in gate_results if gr['passed'])}/{len(gate_results)} passing |")
    md_lines.append("")

    if intent_changes:
        md_lines.append("<details><summary>Intent Documents Changed</summary>")
        md_lines.append("")
        for fp in intent_changes:
            md_lines.append(f"- `{fp}`")
        md_lines.append("")
        md_lines.append("</details>")
        md_lines.append("")

    if covered:
        md_lines.append("<details><summary>Governed Code Changes</summary>")
        md_lines.append("")
        for cid, files in sorted(covered.items()):
            comp = g.nodes.get(cid)
            comp_name = comp.title if comp else cid
            gov = comp_governance.get(cid, {})
            md_lines.append(f"**{comp_name}** (`{cid}`)")
            for fp in files:
                md_lines.append(f"- `{fp}`")
            gov_parts = []
            if gov.get("specs"):
                gov_parts.append("Specs: " + ", ".join(f"`{s['id']}` [{s['status']}]" for s in gov["specs"]))
            if gov.get("adrs"):
                gov_parts.append("ADRs: " + ", ".join(f"`{a['id']}` [{a['status']}]" for a in gov["adrs"]))
            if gov.get("gates"):
                gov_parts.append("Gates: " + ", ".join(f"`{gl['id']}`" for gl in gov["gates"]))
            if gov_parts:
                md_lines.append("> " + " | ".join(gov_parts))
            md_lines.append("")
        md_lines.append("</details>")
        md_lines.append("")

    if uncovered:
        md_lines.append("<details><summary>⚠️ Ungoverned Changes ({} files)</summary>".format(len(uncovered)))
        md_lines.append("")
        md_lines.append("These files are not mapped to any component. Run `sigil suggest <path>` for recommendations.")
        md_lines.append("")
        for fp in uncovered:
            md_lines.append(f"- `{fp}`")
        md_lines.append("")
        md_lines.append("</details>")
        md_lines.append("")

    if gate_results:
        md_lines.append("<details><summary>Gate Results</summary>")
        md_lines.append("")
        for gr in gate_results:
            status_mark = "✅" if gr["passed"] else "❌"
            md_lines.append(f"- {status_mark} **{gr['id']}**: {gr['summary']}")
            for finding in gr["findings"]:
                if isinstance(finding, dict):
                    md_lines.append(f"  - {finding['severity']}: {finding['message']}")
                else:
                    md_lines.append(f"  - {finding}")
        md_lines.append("")
        md_lines.append("</details>")
        md_lines.append("")

    md_lines.append("---")
    md_lines.append("*Generated by [Sigil](https://fielding.github.io/sigil/) — intent-first engineering*")

    comment_body = "\n".join(md_lines)

    # Print to terminal
    print(f"  Coverage: {cov_emoji} {coverage_pct}%  |  Gates: {gate_emoji} {sum(1 for gr in gate_results if gr['passed'])}/{len(gate_results)}")
    print()

    if dry_run:
        print("  --- DRY RUN (comment not posted) ---")
        print()
        print(comment_body)
        return 0

    # Post comment to PR
    try:
        run_cmd(["gh", "pr", "comment", str(pr_number), "--body", comment_body], cwd=repo)
        print(f"  Comment posted to PR #{pr_number}")
        print(f"  {pr_url}")
    except Exception as ex:
        print(f"  Failed to post comment: {ex}")
        print()
        print(comment_body)
        return 1

    return 0


def cmd_doctor(args) -> int:
    """Diagnose sigil installation and repo health."""
    repo = Path(args.repo).resolve()
    checks: List[Tuple[str, bool, str]] = []

    # 1. Python version
    v = sys.version_info
    ok = v >= (3, 11)
    checks.append(("Python >= 3.11", ok, f"{v.major}.{v.minor}.{v.micro}"))

    # 2. PyYAML
    checks.append(("PyYAML installed", yaml is not None, "import yaml" if yaml else "missing — pip install pyyaml"))

    # 3. Git
    try:
        git_v = subprocess.run(["git", "--version"], capture_output=True, text=True)
        checks.append(("Git available", git_v.returncode == 0, git_v.stdout.strip()))
    except FileNotFoundError:
        checks.append(("Git available", False, "not found"))

    # 4. gh CLI
    try:
        gh_v = subprocess.run(["gh", "--version"], capture_output=True, text=True)
        first_line = gh_v.stdout.strip().split("\n")[0] if gh_v.stdout else ""
        checks.append(("GitHub CLI (gh)", gh_v.returncode == 0, first_line))
    except FileNotFoundError:
        checks.append(("GitHub CLI (gh)", False, "not found (optional — needed for sigil pr)"))

    # 5. Directory structure
    expected_dirs = ["components", "intent", "interfaces", "gates", "templates", ".intent"]
    missing = [d for d in expected_dirs if not (repo / d).is_dir()]
    if missing:
        checks.append(("Directory structure", False, f"missing: {', '.join(missing)} — run sigil init"))
    else:
        checks.append(("Directory structure", True, f"{len(expected_dirs)} dirs present"))

    # 6. Config file
    config = repo / ".intent" / "config.yaml"
    checks.append(("Config file", config.exists(), str(config.relative_to(repo)) if config.exists() else "missing — run sigil init"))

    # 7. Templates
    spec_tmpl = repo / "templates" / "SPEC.md"
    adr_tmpl = repo / "templates" / "ADR.md"
    both = spec_tmpl.exists() and adr_tmpl.exists()
    checks.append(("Templates", both, "SPEC.md + ADR.md" if both else "missing — run sigil init"))

    # 8. Graph index
    graph_json = repo / ".intent" / "index" / "graph.json"
    if graph_json.exists():
        try:
            data = json.loads(graph_json.read_text(encoding="utf-8"))
            n = len(data.get("nodes", []))
            e = len(data.get("edges", []))
            checks.append(("Graph index", True, f"{n} nodes, {e} edges"))
        except Exception:
            checks.append(("Graph index", False, "corrupt — run sigil index"))
    else:
        checks.append(("Graph index", False, "not built — run sigil index"))

    # 9. Viewer
    viewer = _find_viewer(repo)
    checks.append(("Viewer", viewer is not None, str(viewer) if viewer else "not found — run sigil init"))

    # 10. Components
    comp_dir = repo / "components"
    comps = list(comp_dir.glob("*.yaml")) if comp_dir.is_dir() else []
    checks.append(("Components", len(comps) > 0, f"{len(comps)} component(s)" if comps else "none — run sigil bootstrap"))

    # 11. Git repo
    git_dir = repo / ".git"
    checks.append(("Git repository", git_dir.is_dir(), "initialized" if git_dir.is_dir() else "not a git repo"))

    # 12. Pre-commit hook
    hook = repo / ".git" / "hooks" / "pre-commit"
    has_hook = hook.exists() and "sigil" in hook.read_text(encoding="utf-8", errors="ignore") if hook.exists() else False
    checks.append(("Pre-commit hook", has_hook, "sigil review --staged" if has_hook else "not installed — run sigil hook install"))

    # Print results
    print()
    print("  Sigil Doctor")
    print("  " + "=" * 50)
    print()
    passed = 0
    failed = 0
    for label, ok, detail in checks:
        icon = "\u2713" if ok else "\u2717"
        status = "ok" if ok else "FAIL"
        print(f"  {icon} {label:.<30s} {status:>4s}  {detail}")
        if ok:
            passed += 1
        else:
            failed += 1
    print()
    print(f"  {passed} passed, {failed} failed")
    if failed == 0:
        print("  Everything looks good.")
    else:
        print("  Run 'sigil init' to fix most issues.")
    print()
    return 0 if failed == 0 else 1


def cmd_map(args) -> int:
    """Render a terminal-friendly dependency map of the intent graph."""
    repo = Path(args.repo).resolve()
    mode = getattr(args, "mode", "tree")
    focus = getattr(args, "focus", None)

    g = build_graph(repo)
    if not g.nodes:
        print("No nodes found. Run `sigil index` first.")
        return 0

    # Build adjacency
    children: Dict[str, List[str]] = collections.defaultdict(list)  # parent -> children
    parents: Dict[str, str] = {}
    for e in g.edges:
        if e.type == "belongs_to" and e.dst in g.nodes:
            if e.src not in children[e.dst]:
                children[e.dst].append(e.src)
            parents[e.src] = e.dst

    # Type symbols
    sym = {"component": "\u25a0", "spec": "\u25c6", "adr": "\u25b2", "gate": "\u25cf", "interface": "\u25c8"}
    type_labels = {"component": "COMP", "spec": "SPEC", "adr": "ADR", "gate": "GATE", "interface": "IFACE"}

    if mode == "tree":
        # Tree view: components as roots, specs/ADRs/gates as children
        print()
        print("  Sigil Intent Map")
        print("  " + "\u2550" * 50)
        print()

        # Roots: components or nodes with no parent
        roots = [n for n in g.nodes.values() if n.type == "component"]
        if not roots:
            roots = [n for n in g.nodes.values() if n.id not in parents]

        # If focusing on a specific node, filter
        if focus:
            focus_upper = focus.upper()
            roots = [n for n in roots if focus_upper in n.id.upper() or focus_upper in n.title.upper()]
            if not roots:
                # Maybe it's a child node — find its root
                for n in g.nodes.values():
                    if focus_upper in n.id.upper() or focus_upper in n.title.upper():
                        root_id = parents.get(n.id)
                        if root_id and root_id in g.nodes:
                            roots = [g.nodes[root_id]]
                        else:
                            roots = [n]
                        break

        for ri, root in enumerate(sorted(roots, key=lambda n: n.id)):
            s = sym.get(root.type, "\u25cb")
            print(f"  {s} {root.id}  {root.title}")

            # Get children grouped by type
            kids = children.get(root.id, [])
            kid_nodes = [g.nodes[k] for k in kids if k in g.nodes]
            kid_nodes.sort(key=lambda n: (n.type, n.id))

            # Also find gates that apply to children
            gate_targets: Dict[str, List[str]] = collections.defaultdict(list)
            for e in g.edges:
                if e.type == "gated_by":
                    gate_targets[e.dst].append(e.src)

            for ki, kid in enumerate(kid_nodes):
                is_last = ki == len(kid_nodes) - 1
                connector = "\u2514\u2500\u2500" if is_last else "\u251c\u2500\u2500"
                ks = sym.get(kid.type, "\u25cb")
                # Get status from frontmatter
                status_str = ""
                try:
                    md = read_text(repo / kid.path)
                    fm, _ = parse_front_matter(md)
                    st = fm.get("status", "")
                    if st:
                        status_str = f"  [{st}]"
                except Exception:
                    pass
                print(f"  {connector} {ks} {kid.id}  {kid.title}{status_str}")

                # Show gates on this node
                for e in g.edges:
                    if e.type == "gated_by" and e.src == kid.id and e.dst in g.nodes:
                        gate_node = g.nodes[e.dst]
                        prefix = "     " if is_last else "\u2502    "
                        print(f"  {prefix}\u2514\u2500 {sym.get('gate', '\u25cf')} {gate_node.id}")

            # Show edges to other components
            outgoing = []
            for e in g.edges:
                if e.src == root.id and e.type not in ("belongs_to",) and e.dst in g.nodes:
                    outgoing.append(e)
            if outgoing:
                for e in outgoing:
                    dst = g.nodes[e.dst]
                    print(f"      \u2192 {e.type} {dst.id}")

            if ri < len(roots) - 1:
                print()

        # Legend
        print()
        print("  " + "\u2500" * 50)
        legend_parts = [f"{sym.get(t, '\u25cb')} {type_labels.get(t, t)}" for t in ["component", "spec", "adr", "gate", "interface"] if any(n.type == t for n in g.nodes.values())]
        print("  " + "  ".join(legend_parts))
        print(f"  {len(g.nodes)} nodes, {len(g.edges)} edges")
        print()

    elif mode == "deps":
        # Dependency view: show all cross-component edges
        print()
        print("  Sigil Dependency Map")
        print("  " + "\u2550" * 50)
        print()

        # Collect cross-component edges
        dep_types = {"depends_on", "consumes", "provides", "relates_to", "supersedes"}
        deps = [e for e in g.edges if e.type in dep_types and e.src in g.nodes and e.dst in g.nodes]

        if not deps:
            print("  No cross-node dependencies found.")
        else:
            for e in sorted(deps, key=lambda e: (e.src, e.type)):
                src = g.nodes[e.src]
                dst = g.nodes[e.dst]
                arrow = "\u2192" if e.type in ("depends_on", "consumes") else "\u2190" if e.type == "provides" else "\u2194"
                print(f"  {src.id} {arrow} {dst.id}  ({e.type})")

        print()

    elif mode == "flat":
        # Flat list grouped by type
        print()
        print("  Sigil Node Registry")
        print("  " + "\u2550" * 50)
        print()

        by_type: Dict[str, List] = collections.defaultdict(list)
        for n in g.nodes.values():
            by_type[n.type].append(n)

        for t in ["component", "spec", "adr", "gate", "interface"]:
            nodes = by_type.get(t, [])
            if not nodes:
                continue
            label = type_labels.get(t, t).upper()
            print(f"  {sym.get(t, '\u25cb')} {label} ({len(nodes)})")
            for n in sorted(nodes, key=lambda n: n.id):
                status_str = ""
                try:
                    md = read_text(repo / n.path)
                    fm, _ = parse_front_matter(md)
                    st = fm.get("status", "")
                    if st:
                        status_str = f"  [{st}]"
                except Exception:
                    pass
                print(f"    {n.id:<20s} {n.title}{status_str}")
            print()

        print(f"  {len(g.nodes)} nodes, {len(g.edges)} edges")
        print()

    return 0


def cmd_why(args) -> int:
    """Explain why a file exists by tracing its full intent chain with excerpts."""
    import fnmatch as fnm

    repo = Path(args.repo).resolve()
    target = args.path
    g = build_graph(repo)

    # Resolve path
    target_path = Path(target)
    if target_path.is_absolute():
        try:
            target_path = target_path.relative_to(repo)
        except ValueError:
            pass
    target_str = str(target_path).replace("\\", "/")

    # Check file exists
    full_path = repo / target_str
    if not full_path.exists():
        print(f"  File not found: {target_str}")
        return 1

    print()
    print(f"  sigil why {target_str}")
    print(f"  {'=' * 50}")

    # 1. Find owning components
    owning_components: List[str] = []
    comp_dir = repo / "components"
    if comp_dir.is_dir():
        for p in comp_dir.glob("*.yaml"):
            data = load_yaml(p) if yaml else {}
            cid = data.get("id") or f"COMP-{p.stem}"
            for pattern in data.get("paths", []):
                if fnm.fnmatch(target_str, pattern):
                    owning_components.append(cid)
                    break

    if not owning_components:
        print(f"\n  This file is ungoverned — no component claims it.")
        print(f"  To govern it, add a path pattern to a component YAML:")
        print(f"    paths:")
        print(f'      - "{target_str}"')
        print()
        return 0

    for comp_id in owning_components:
        comp = g.nodes.get(comp_id)
        if not comp:
            continue

        print(f"\n  Owned by: {comp.title} ({comp_id})")
        print(f"  {comp.path}")

        # Collect all related nodes with their relationships (deduplicated)
        seen_ids: set = set()
        specs, adrs, gates, interfaces = [], [], [], []
        for e in g.edges:
            if e.dst == comp_id and e.type == "belongs_to":
                node = g.nodes.get(e.src)
                if node and node.id not in seen_ids:
                    seen_ids.add(node.id)
                    if node.type == "spec":
                        specs.append(node)
                    elif node.type == "adr":
                        adrs.append(node)
                    elif node.type == "gate":
                        gates.append(node)
            if e.type == "gated_by" and (e.src == comp_id or e.dst == comp_id):
                gid = e.dst if e.src == comp_id else e.src
                gnode = g.nodes.get(gid)
                if gnode and gnode not in gates:
                    gates.append(gnode)
            if e.type in ("provides", "consumes") and (e.src == comp_id or e.dst == comp_id):
                iid = e.dst if e.src == comp_id else e.src
                inode = g.nodes.get(iid)
                if inode and inode.type == "interface" and inode not in interfaces:
                    interfaces.append(inode)

        # Also find gates that apply to any of this component's specs
        spec_ids = {s.id for s in specs}
        for e in g.edges:
            if e.type == "gated_by" and e.src in spec_ids:
                gnode = g.nodes.get(e.dst)
                if gnode and gnode not in gates:
                    gates.append(gnode)

        def _excerpt(node_path: str, max_lines: int = 4) -> str:
            """Extract a meaningful excerpt from an intent doc."""
            try:
                md = read_text(repo / node_path)
                _, body = parse_front_matter(md)
                # Find Intent or Context section
                lines = body.strip().splitlines()
                capture = False
                result = []
                for line in lines:
                    if line.strip().startswith("## Intent") or line.strip().startswith("## Context") or line.strip().startswith("## Decision"):
                        capture = True
                        continue
                    elif line.strip().startswith("## ") and capture:
                        break
                    elif capture and line.strip():
                        result.append(line.strip())
                        if len(result) >= max_lines:
                            break
                if not result:
                    # Fallback: first non-empty body lines after title
                    for line in lines:
                        if line.strip() and not line.startswith("#"):
                            result.append(line.strip())
                            if len(result) >= max_lines:
                                break
                return "\n".join(result)
            except Exception:
                return ""

        # Print the intent chain as a narrative
        if specs:
            print(f"\n  What is being built:")
            for spec in sorted(specs, key=lambda n: n.id):
                md = read_text(repo / spec.path)
                fm, _ = parse_front_matter(md)
                status = fm.get("status", "?")
                print(f"    [{status}] {spec.id}: {spec.title}")
                excerpt = _excerpt(spec.path)
                if excerpt:
                    for line in excerpt.splitlines():
                        print(f"      | {line}")

        if adrs:
            print(f"\n  Why it was built this way:")
            for adr in sorted(adrs, key=lambda n: n.id):
                md = read_text(repo / adr.path)
                fm, _ = parse_front_matter(md)
                status = fm.get("status", "?")
                print(f"    [{status}] {adr.id}: {adr.title}")
                excerpt = _excerpt(adr.path)
                if excerpt:
                    for line in excerpt.splitlines():
                        print(f"      | {line}")

        if gates:
            print(f"\n  What enforces it:")
            for gate in sorted(gates, key=lambda n: n.id):
                print(f"    {gate.id}: {gate.title}")

        if interfaces:
            print(f"\n  Contracts:")
            for iface in sorted(interfaces, key=lambda n: n.id):
                print(f"    {iface.id}: {iface.title}")

        # Show transitive dependencies — what else depends on these specs
        dep_chain = []
        for spec in specs:
            for e in g.edges:
                if e.type == "depends_on" and e.dst == spec.id and e.src in g.nodes:
                    dep_chain.append((g.nodes[e.src], spec))
                if e.type == "depends_on" and e.src == spec.id and e.dst in g.nodes:
                    dep_chain.append((spec, g.nodes[e.dst]))

        if dep_chain:
            print(f"\n  Connected decisions:")
            seen = set()
            for src, dst in dep_chain:
                key = f"{src.id}->{dst.id}"
                if key not in seen:
                    seen.add(key)
                    print(f"    {src.id} depends on {dst.id} ({dst.title})")

    print()
    return 0


def _blast_radius(node_id: str, g: Graph, max_depth: int = 3) -> List[List[Dict]]:
    """BFS traversal returning concentric rings of connected nodes.

    Each ring is a list of dicts: {id, type, edge_type, direction}.
    Ring 0 = direct connections, Ring 1 = secondary, etc.
    """
    rings: List[List[Dict]] = []
    visited = {node_id}

    def get_connected(nid: str) -> List[Dict]:
        out: List[Dict] = []
        for e in g.edges:
            if e.src == nid and e.dst not in visited and e.dst in g.nodes:
                out.append({"id": e.dst, "type": g.nodes[e.dst].type,
                            "edge_type": e.type, "direction": "out"})
            if e.dst == nid and e.src not in visited and e.src in g.nodes:
                out.append({"id": e.src, "type": g.nodes[e.src].type,
                            "edge_type": e.type, "direction": "in"})
        return out

    frontier = [node_id]
    for _ in range(max_depth):
        ring: List[Dict] = []
        next_frontier: List[str] = []
        for nid in frontier:
            for item in get_connected(nid):
                if item["id"] not in visited:
                    visited.add(item["id"])
                    ring.append(item)
                    next_frontier.append(item["id"])
        rings.append(ring)
        frontier = next_frontier
        if not frontier:
            break

    return rings


def _resolve_node_id(query: str, g: Graph) -> Optional[str]:
    """Resolve a query to a node ID, supporting exact match and fuzzy prefix."""
    # Exact match
    if query in g.nodes:
        return query
    # Case-insensitive exact
    upper = query.upper()
    for nid in g.nodes:
        if nid.upper() == upper:
            return nid
    # Prefix match
    matches = [nid for nid in g.nodes if nid.upper().startswith(upper)]
    if len(matches) == 1:
        return matches[0]
    # Substring match
    matches = [nid for nid in g.nodes if upper in nid.upper()]
    if len(matches) == 1:
        return matches[0]
    # Title search
    matches = [nid for nid in g.nodes if upper in g.nodes[nid].title.upper()]
    if len(matches) == 1:
        return matches[0]
    if matches:
        return None  # ambiguous
    return None


def cmd_impact(args) -> int:
    """Show the blast radius of a node — what depends on it and what it affects."""
    repo = Path(args.repo).resolve()
    query = args.node
    as_json = getattr(args, "json", False)
    max_depth = int(getattr(args, "depth", 3))

    g = build_graph(repo)

    node_id = _resolve_node_id(query, g)
    if not node_id:
        # Show candidates
        upper = query.upper()
        candidates = [nid for nid in g.nodes if upper in nid.upper() or upper in g.nodes[nid].title.upper()]
        if candidates:
            print(f"  Ambiguous query '{query}'. Did you mean one of:")
            for c in sorted(candidates)[:10]:
                print(f"    {c}  {g.nodes[c].title}")
        else:
            print(f"  No node found matching '{query}'.")
            print(f"  Available nodes: {', '.join(sorted(g.nodes.keys())[:20])}")
        return 1

    node = g.nodes[node_id]
    rings = _blast_radius(node_id, g, max_depth=max_depth)

    if as_json:
        result = {
            "node": {"id": node.id, "type": node.type, "title": node.title, "path": node.path},
            "rings": [],
            "summary": {},
        }
        type_counts: Dict[str, int] = collections.defaultdict(int)
        for ri, ring in enumerate(rings):
            ring_data = []
            for item in ring:
                ring_data.append(item)
                type_counts[item["type"]] += 1
            result["rings"].append({"depth": ri + 1, "nodes": ring_data})
        total = sum(len(r) for r in rings)
        result["summary"] = {"total": total, "by_type": dict(type_counts)}
        print(json.dumps(result, indent=2))
        return 0

    # Terminal output
    sym = {
        "component": "\u25a0", "spec": "\u25c6", "adr": "\u25b2",
        "gate": "\u25cf", "interface": "\u25c8",
    }
    ring_names = ["Direct", "Secondary", "Tertiary"]
    # Extend ring names for deeper traversals
    while len(ring_names) < max_depth:
        ring_names.append(f"Ring {len(ring_names) + 1}")

    dir_arrows = {"out": "\u2192", "in": "\u2190"}

    print()
    print(f"  sigil impact {node.id}")
    print(f"  {'=' * 50}")
    print(f"  {sym.get(node.type, '\u25cb')} {node.id}: {node.title}")
    print(f"  {node.path}")

    total = 0
    type_counts: Dict[str, int] = collections.defaultdict(int)

    for ri, ring in enumerate(rings):
        if not ring:
            continue
        total += len(ring)
        print(f"\n  {ring_names[ri]} ({len(ring)})")
        print(f"  {'-' * 40}")
        for item in sorted(ring, key=lambda x: (x["type"], x["id"])):
            type_counts[item["type"]] += 1
            s = sym.get(item["type"], "\u25cb")
            arrow = dir_arrows.get(item["direction"], "\u2194")
            target = g.nodes[item["id"]]
            print(f"    {arrow} {s} {item['id']}  {target.title}  ({item['edge_type']})")

    # Summary
    print(f"\n  {'=' * 50}")
    if total == 0:
        print("  No connected nodes found — this node is isolated.")
    else:
        parts = [f"{count} {t}{'s' if count != 1 else ''}" for t, count in sorted(type_counts.items())]
        print(f"  Blast radius: {total} node(s) — {', '.join(parts)}")
    print()
    return 0


def cmd_scan(args) -> int:
    """Deep-scan a codebase to auto-detect components, APIs, decisions, and relationships."""
    repo = Path(args.repo).resolve()
    dry_run = getattr(args, "dry_run", False)
    out_path = getattr(args, "output", None)

    print()
    print("  Sigil Scan")
    print("  " + "=" * 50)
    print()

    # --- 1. Detect components (deeper than bootstrap) ---
    # Skip sigil's own structure dirs in addition to standard skip dirs
    scan_skip = _SKIP_DIRS | {"components", "intent", "interfaces", "gates", "templates", "docs"}
    components: List[dict] = []
    for child in sorted(repo.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name in scan_skip:
            continue
        info: dict = {"slug": child.name.lower().replace(" ", "-"), "path": child.name, "lang": None, "detected_via": None, "files": 0, "has_readme": False, "has_tests": False, "has_dockerfile": False}
        for manifest, lang in _MANIFEST_PATTERNS:
            if (child / manifest).exists():
                info["lang"] = lang
                info["detected_via"] = manifest
                break
        # Count source files
        try:
            info["files"] = sum(1 for _ in child.rglob("*") if _.is_file() and not any(s in str(_) for s in [".git", "node_modules", "__pycache__", ".venv"]))
        except Exception:
            pass
        info["has_readme"] = any((child / r).exists() for r in ["README.md", "readme.md", "README.rst", "README"])
        info["has_tests"] = any(d.exists() for d in [child / "tests", child / "test", child / "__tests__", child / "spec"]) or bool(list(child.glob("*_test.*")) + list(child.glob("test_*.*")))
        info["has_dockerfile"] = (child / "Dockerfile").exists() or (child / "dockerfile").exists()
        if info["lang"] or info["files"] > 2:
            components.append(info)

    # --- 2. Detect APIs ---
    apis: List[dict] = []
    api_patterns = [
        ("openapi.yaml", "OpenAPI"), ("openapi.yml", "OpenAPI"), ("openapi.json", "OpenAPI"),
        ("swagger.yaml", "Swagger"), ("swagger.yml", "Swagger"), ("swagger.json", "Swagger"),
        ("schema.graphql", "GraphQL"), ("schema.gql", "GraphQL"),
    ]
    for pat_file, api_type in api_patterns:
        for found in repo.rglob(pat_file):
            if any(s in str(found) for s in [".git", "node_modules", "__pycache__", ".venv"]):
                continue
            apis.append({"path": str(found.relative_to(repo)), "type": api_type})
    # Proto files
    for proto in repo.rglob("*.proto"):
        if not any(s in str(proto) for s in [".git", "node_modules", "__pycache__", ".venv"]):
            apis.append({"path": str(proto.relative_to(repo)), "type": "gRPC/Protobuf"})

    # --- 3. Detect architectural decisions in READMEs ---
    decisions: List[dict] = []
    decision_keywords = re.compile(r"\b(decided|decision|chose|chosen|trade-?off|alternative|option|rationale|why we|we chose|we decided|architecture)\b", re.I)
    for readme in repo.rglob("README*"):
        if any(s in str(readme) for s in [".git", "node_modules", "__pycache__", ".venv"]):
            continue
        try:
            text = readme.read_text(encoding="utf-8", errors="ignore")[:10000]
            matches = decision_keywords.findall(text)
            if len(matches) >= 2:
                decisions.append({"path": str(readme.relative_to(repo)), "signals": len(matches)})
        except Exception:
            pass
    # ADR directories
    for adr_dir_name in ["adr", "adrs", "decisions", "docs/adr", "docs/decisions", "doc/adr"]:
        adr_dir = repo / adr_dir_name
        if adr_dir.is_dir():
            for f in adr_dir.iterdir():
                if f.suffix in (".md", ".txt", ".rst"):
                    decisions.append({"path": str(f.relative_to(repo)), "signals": 10})

    # --- 4. Detect CI/CD ---
    ci_files: List[dict] = []
    ci_patterns = [
        (".github/workflows", "GitHub Actions"),
        (".gitlab-ci.yml", "GitLab CI"),
        ("Jenkinsfile", "Jenkins"),
        (".circleci", "CircleCI"),
        (".travis.yml", "Travis CI"),
        ("azure-pipelines.yml", "Azure Pipelines"),
        ("cloudbuild.yaml", "Cloud Build"),
        ("Makefile", "Makefile"),
        ("Taskfile.yml", "Taskfile"),
    ]
    for ci_path, ci_type in ci_patterns:
        p = repo / ci_path
        if p.exists():
            if p.is_dir():
                for f in p.iterdir():
                    ci_files.append({"path": str(f.relative_to(repo)), "type": ci_type})
            else:
                ci_files.append({"path": ci_path, "type": ci_type})

    # --- 5. Detect config/infra ---
    infra: List[dict] = []
    infra_patterns = [
        ("docker-compose.yml", "Docker Compose"), ("docker-compose.yaml", "Docker Compose"),
        ("Dockerfile", "Docker"), ("terraform", "Terraform"), ("k8s", "Kubernetes"),
        ("kubernetes", "Kubernetes"), ("helm", "Helm"), (".env.example", "Environment"),
    ]
    for inf_path, inf_type in infra_patterns:
        p = repo / inf_path
        if p.exists():
            infra.append({"path": inf_path, "type": inf_type})

    # --- 6. Existing sigil coverage ---
    existing_components = set()
    comp_dir = repo / "components"
    if comp_dir.is_dir():
        for cy in comp_dir.glob("*.yaml"):
            existing_components.add(cy.stem)
    existing_specs = len(list((repo / "intent").rglob("specs/**/*.md"))) if (repo / "intent").is_dir() else 0
    existing_adrs = len(list((repo / "intent").rglob("adrs/**/*.md"))) if (repo / "intent").is_dir() else 0
    existing_gates = len(list((repo / "gates").glob("*.yaml"))) if (repo / "gates").is_dir() else 0

    # --- Build report ---
    report: dict = {
        "components": components,
        "apis": apis,
        "decisions": decisions,
        "ci": ci_files,
        "infra": infra,
        "existing_coverage": {
            "components": len(existing_components),
            "specs": existing_specs,
            "adrs": existing_adrs,
            "gates": existing_gates,
        },
        "recommendations": [],
    }

    # Generate recommendations
    recs = report["recommendations"]
    uncovered = [c for c in components if c["slug"] not in existing_components]
    if uncovered:
        recs.append(f"Create component YAML for {len(uncovered)} detected component(s): {', '.join(c['slug'] for c in uncovered[:5])}")
    if apis and existing_specs == 0:
        recs.append(f"Found {len(apis)} API definition(s) but no specs. Create specs to govern API contracts.")
    if decisions and existing_adrs == 0:
        recs.append(f"Found {len(decisions)} file(s) with decision language but no ADRs. Formalize decisions with sigil new adr.")
    if existing_gates == 0 and (existing_specs > 0 or len(components) > 2):
        recs.append("No gates defined. Add gates/ YAML to enforce spec compliance in CI.")
    dockerized = [c for c in components if c["has_dockerfile"]]
    no_tests = [c for c in components if not c["has_tests"] and c["lang"]]
    if no_tests:
        recs.append(f"{len(no_tests)} component(s) have no test directory: {', '.join(c['slug'] for c in no_tests[:5])}")
    if not ci_files:
        recs.append("No CI/CD detected. Run sigil ci --init to generate a GitHub Actions workflow.")

    # --- Print report ---
    print(f"  Components detected:  {len(components)}")
    for c in components:
        cov = "covered" if c["slug"] in existing_components else "NEW"
        lang = c["lang"] or "unknown"
        extras = []
        if c["has_tests"]:
            extras.append("tests")
        if c["has_dockerfile"]:
            extras.append("docker")
        if c["has_readme"]:
            extras.append("readme")
        extra_str = f"  [{', '.join(extras)}]" if extras else ""
        print(f"    {cov:>7s}  {c['slug']:<25s} {lang:<10s} {c['files']:>4d} files{extra_str}")

    if apis:
        print(f"\n  APIs detected:        {len(apis)}")
        for a in apis:
            print(f"           {a['type']:<15s} {a['path']}")

    if decisions:
        print(f"\n  Decision signals:     {len(decisions)}")
        for d in decisions[:5]:
            print(f"           {d['signals']:>2d} signals   {d['path']}")

    if ci_files:
        print(f"\n  CI/CD detected:       {len(ci_files)}")
        for c in ci_files:
            print(f"           {c['type']:<18s} {c['path']}")

    if infra:
        print(f"\n  Infrastructure:       {len(infra)}")
        for i in infra:
            print(f"           {i['type']:<18s} {i['path']}")

    cov = report["existing_coverage"]
    print(f"\n  Sigil coverage:")
    print(f"    Components: {cov['components']}  Specs: {cov['specs']}  ADRs: {cov['adrs']}  Gates: {cov['gates']}")

    if recs:
        print(f"\n  Recommendations:")
        for i, r in enumerate(recs, 1):
            print(f"    {i}. {r}")

    print()

    # --- Write report JSON ---
    if out_path:
        report_path = Path(out_path)
    else:
        idx_dir = repo / ".intent" / "index"
        idx_dir.mkdir(parents=True, exist_ok=True)
        report_path = idx_dir / "scan.json"
    if not dry_run:
        # Convert to serializable
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  Report written to {report_path.relative_to(repo)}")
    else:
        print("  [dry-run] Would write report to", report_path)

    return 0


def cmd_ci(args) -> int:
    """Run the full CI pipeline: index, check, review, badge, export."""
    repo = Path(args.repo).resolve()
    strict = getattr(args, "strict", False)
    base = getattr(args, "base", None)
    head = getattr(args, "head", None)

    print()
    print("  Sigil CI Pipeline")
    print("  " + "=" * 50)
    print()

    errors = 0

    # Step 1: Index
    print("  [1/5] Indexing...")
    g = build_graph(repo)
    write_graph_artifacts(repo, g)
    print(f"         {len(g.nodes)} nodes, {len(g.edges)} edges")

    # Step 2: Lint
    print("  [2/5] Linting...")
    _repo_str = str(repo)

    class LintArgs:
        repo = _repo_str
        min_severity = "warn"
    lint_result = cmd_lint(LintArgs())
    if lint_result != 0:
        errors += 1
        print("         Lint issues found")
    else:
        print("         Clean")

    # Step 3: Check gates
    print("  [3/5] Checking gates...")
    class CheckArgs:
        repo = _repo_str
    check_result = cmd_check(CheckArgs())
    if check_result != 0:
        errors += 1
        print("         Gate failures detected")
    else:
        print("         All gates passing")

    # Step 4: Badge
    print("  [4/5] Generating badge...")
    badge_path = repo / ".intent" / "badge.svg"
    class BadgeArgs:
        repo = _repo_str
        output = str(badge_path)
    cmd_badge(BadgeArgs())
    print(f"         {badge_path.relative_to(repo)}")

    # Step 5: Review (if in a git context with changes)
    print("  [5/5] Review...")
    class ReviewArgs:
        repo = _repo_str
        staged = False
        json = False
    ReviewArgs.base = base
    ReviewArgs.head = head
    try:
        review_result = cmd_review(ReviewArgs())
    except (subprocess.CalledProcessError, Exception):
        review_result = 0
        print("         No changes to review")

    # Summary
    print()
    print("  " + "-" * 50)
    if errors == 0:
        print("  Pipeline: PASS")
    elif strict:
        print("  Pipeline: FAIL (strict mode)")
    else:
        print(f"  Pipeline: WARN ({errors} issue(s), non-blocking)")
    print()

    if strict and errors > 0:
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="sigil", description="Sigil — intent-first engineering CLI")
    ap.add_argument("--repo", default=".", help="Repo root (default: cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("status", help="Show intent graph health status")
    sp.set_defaults(fn=cmd_status)

    sp = sub.add_parser("index", help="Build graph index from repo")
    sp.set_defaults(fn=cmd_index)

    sp = sub.add_parser("diff", help="Compute graph diff between two commits")
    sp.add_argument("base", help="Base commit SHA")
    sp.add_argument("head", help="Head commit SHA")
    sp.add_argument("--out", default=None, help="Output diff JSON path")
    sp.add_argument("--md", default=None, help="Output diff markdown path")
    sp.set_defaults(fn=cmd_diff)

    sp = sub.add_parser("new", help="Create a new intent document from template")
    sp.add_argument("type", choices=["spec", "adr"], help="Document type")
    sp.add_argument("component", help="Component slug")
    sp.add_argument("title", help="Document title")
    sp.set_defaults(fn=cmd_new)

    sp = sub.add_parser("lint", help="Lint intent documents")
    sp.add_argument("--min-severity", default="warn", choices=["error", "warn", "info"],
                    dest="min_severity", help="Minimum severity to report (default: warn)")
    sp.set_defaults(fn=cmd_lint)

    sp = sub.add_parser("fmt", help="Normalize intent documents (IDs, Links section)")
    sp.set_defaults(fn=cmd_fmt)

    sp = sub.add_parser("bootstrap", help="Scan repo and create missing component stubs")
    sp.add_argument("--dry-run", action="store_true", help="Print what would be created without writing files")
    sp.set_defaults(fn=cmd_bootstrap)

    sp = sub.add_parser("init", help="Zero-to-working setup: scaffold, index, and open viewer")
    sp.add_argument("--port", default="8787", help="Port for local viewer server (default: 8787)")
    sp.set_defaults(fn=cmd_init)

    sp = sub.add_parser("drift", help="Detect drift between intent graph and codebase")
    sp.set_defaults(fn=cmd_drift)

    sp = sub.add_parser("check", help="Run gate enforcement checks against the intent graph")
    sp.add_argument("--json", action="store_true", default=False, help="Output results as JSON")
    sp.set_defaults(fn=cmd_check)

    sp = sub.add_parser("export", help="Generate self-contained HTML snapshot of the viewer")
    sp.add_argument("--output", "-o", default=None, help="Output path (default: .intent/export.html)")
    sp.set_defaults(fn=cmd_export)

    sp = sub.add_parser("coverage", help="Show intent coverage report with health score")
    sp.add_argument("--json", action="store_true", default=False, help="Output results as JSON")
    sp.set_defaults(fn=cmd_coverage)

    sp = sub.add_parser("badge", help="Generate intent coverage badge SVG")
    sp.add_argument("--output", "-o", default=None, help="Output path (default: .intent/badge.svg)")
    sp.set_defaults(fn=cmd_badge)

    sp = sub.add_parser("serve", help="Start dev server with file watching and auto-rebuild")
    sp.add_argument("--port", default="8787", help="Port for dev server (default: 8787)")
    sp.set_defaults(fn=cmd_serve)

    sp = sub.add_parser("ask", help="Search intent docs with a natural-language question")
    sp.add_argument("question", help="Question to search for")
    sp.add_argument("--top", type=int, default=5, help="Number of results to return (default: 5)")
    sp.add_argument("--json", action="store_true", default=False, help="Output results as JSON")
    sp.set_defaults(fn=cmd_ask)

    sp = sub.add_parser("suggest", help="Show which intent docs govern a file")
    sp.add_argument("path", help="File path to analyze")
    sp.set_defaults(fn=cmd_suggest)

    sp = sub.add_parser("review", help="Analyze git diff for intent coverage of changed files")
    sp.add_argument("base", nargs="?", default=None, help="Base commit (default: HEAD)")
    sp.add_argument("head", nargs="?", default=None, help="Head commit (default: working tree)")
    sp.add_argument("--staged", action="store_true", help="Review staged changes only")
    sp.add_argument("--json", action="store_true", help="Output JSON instead of terminal report")
    sp.set_defaults(fn=cmd_review)

    sp = sub.add_parser("timeline", help="Build a timeline of intent evolution from git history")
    sp.add_argument("--max", default="50", help="Maximum number of commits to scan (default: 50)")
    sp.add_argument("--output", "-o", default=None, help="Output path (default: .intent/index/timeline.json)")
    sp.set_defaults(fn=cmd_timeline)

    sp = sub.add_parser("hook", help="Install/uninstall Sigil git pre-commit hook")
    sp.add_argument("action", choices=["install", "uninstall", "status"], help="Action to perform")
    sp.set_defaults(fn=cmd_hook)

    sp = sub.add_parser("pr", help="Analyze a GitHub PR for intent coverage and post a comment")
    sp.add_argument("number", nargs="?", type=int, default=None, help="PR number (default: current branch PR)")
    sp.add_argument("--dry-run", action="store_true", help="Print comment without posting")
    sp.set_defaults(fn=cmd_pr)

    sp = sub.add_parser("doctor", help="Diagnose sigil installation and repo health")
    sp.set_defaults(fn=cmd_doctor)

    sp = sub.add_parser("scan", help="Deep-scan codebase to detect components, APIs, decisions, and relationships")
    sp.add_argument("--dry-run", action="store_true", help="Print findings without writing report")
    sp.add_argument("--output", "-o", default=None, help="Output path for scan report JSON")
    sp.set_defaults(fn=cmd_scan)

    sp = sub.add_parser("ci", help="Run full CI pipeline: index, lint, check, badge, review")
    sp.add_argument("--strict", action="store_true", help="Exit non-zero on any warnings")
    sp.add_argument("base", nargs="?", default=None, help="Base commit for review (optional)")
    sp.add_argument("head", nargs="?", default=None, help="Head commit for review (optional)")
    sp.set_defaults(fn=cmd_ci)

    sp = sub.add_parser("map", help="Render terminal-friendly dependency map of the intent graph")
    sp.add_argument("--mode", choices=["tree", "deps", "flat"], default="tree", help="Display mode (default: tree)")
    sp.add_argument("--focus", default=None, help="Focus on a specific node or component")
    sp.set_defaults(fn=cmd_map)

    sp = sub.add_parser("why", help="Explain why a file exists by tracing its full intent chain")
    sp.add_argument("path", help="File path to trace")
    sp.set_defaults(fn=cmd_why)

    sp = sub.add_parser("impact", help="Show blast radius — what depends on a node and what it affects")
    sp.add_argument("node", help="Node ID or search term (e.g. COMP-auth, SPEC-0001)")
    sp.add_argument("--depth", default="3", help="Max traversal depth (default: 3)")
    sp.add_argument("--json", action="store_true", default=False, help="Output results as JSON")
    sp.set_defaults(fn=cmd_impact)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
