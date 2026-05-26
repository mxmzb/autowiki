from __future__ import annotations

import json
import re
from collections import deque

import networkx as nx

from .config import WikiConfig
from .pages import list_page_paths, load_page

_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")


def build_graph(cfg: WikiConfig) -> nx.DiGraph:
    """Build the knowledge graph from page frontmatter + wiki-links (computed on demand)."""
    g: nx.DiGraph = nx.DiGraph()
    parsed = []
    for path_ in list_page_paths(cfg):
        try:
            fm, body = load_page(path_)
        except Exception:
            continue
        slug = fm.slug or path_.stem
        g.add_node(slug, type=fm.type or "untyped", title=fm.title or slug)
        parsed.append((slug, fm, body))

    def edge(src: str, raw, predicate: str) -> None:
        dst = str(raw).strip()
        if dst and dst in g:  # skip edges to unknown targets (lint reports them)
            g.add_edge(src, dst, predicate=predicate)

    for slug, fm, body in parsed:
        for target in _LINK_RE.findall(body):
            edge(slug, target, "links")
        for target in fm.related:
            edge(slug, target, "related")
        for target in fm.supersedes:
            edge(slug, target, "supersedes")
        for target in fm.superseded_by:
            edge(slug, target, "superseded_by")
        for target in fm.contradicts:
            edge(slug, target, "contradicts")
        for rel in fm.relations:
            if isinstance(rel, dict) and rel.get("target"):
                edge(slug, rel["target"], str(rel.get("predicate") or "related"))

    return g


def neighbors(g: nx.DiGraph, slug: str, depth: int = 1, predicate: str | None = None) -> list[dict]:
    """Nodes reachable from `slug` within `depth` (undirected), optionally via one predicate."""
    if slug not in g:
        raise KeyError(slug)
    adj: dict[str, set[str]] = {n: set() for n in g.nodes}
    for u, v, data in g.edges(data=True):
        if predicate is None or data.get("predicate") == predicate:
            adj[u].add(v)
            adj[v].add(u)

    dist = {slug: 0}
    queue = deque([slug])
    while queue:
        cur = queue.popleft()
        if dist[cur] >= depth:
            continue
        for nb in adj[cur]:
            if nb not in dist:
                dist[nb] = dist[cur] + 1
                queue.append(nb)

    results = [
        {"slug": n, "title": g.nodes[n].get("title", n), "distance": dist[n]}
        for n in dist
        if n != slug
    ]
    results.sort(key=lambda r: (r["distance"], r["slug"]))
    return results


def path(g: nx.DiGraph, a: str, b: str) -> list[str] | None:
    """Shortest undirected path (list of slugs), or None if missing/disconnected."""
    if a not in g or b not in g:
        return None
    undirected = g.to_undirected(as_view=True)
    try:
        return nx.shortest_path(undirected, a, b)
    except nx.NetworkXNoPath:
        return None


def hubs(g: nx.DiGraph, limit: int = 10) -> list[dict]:
    """Most-connected pages by total (in+out) degree."""
    ranked = sorted(g.degree(), key=lambda kv: (-kv[1], kv[0]))
    return [{"slug": n, "title": g.nodes[n].get("title", n), "degree": d} for n, d in ranked[:limit]]


def stats(g: nx.DiGraph) -> dict:
    by_type: dict[str, int] = {}
    for _node, data in g.nodes(data=True):
        key = data.get("type", "untyped")
        by_type[key] = by_type.get(key, 0) + 1
    isolated = sum(1 for n in g.nodes if g.degree(n) == 0)
    return {
        "nodes": g.number_of_nodes(),
        "edges": g.number_of_edges(),
        "by_type": by_type,
        "isolated": isolated,
    }


def export(g: nx.DiGraph, fmt: str) -> str:
    if fmt == "json":
        try:
            data = nx.node_link_data(g, edges="links")
        except TypeError:  # older networkx without the `edges` kwarg
            data = nx.node_link_data(g)
        return json.dumps(data)
    if fmt == "dot":
        lines = ["digraph wiki {"]
        for node, data in g.nodes(data=True):
            label = str(data.get("title", node)).replace('"', "'")
            lines.append(f'  "{node}" [label="{label}"];')
        for u, v, data in g.edges(data=True):
            predicate = str(data.get("predicate", "")).replace('"', "'")
            lines.append(f'  "{u}" -> "{v}" [label="{predicate}"];')
        lines.append("}")
        return "\n".join(lines) + "\n"
    raise ValueError(f"unknown export format: {fmt!r} (use 'json' or 'dot')")
