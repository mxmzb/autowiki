import json

from llm_wiki.config import WikiConfig
from llm_wiki.frontmatter import dump, parse
from llm_wiki.graph import build_graph, export, hubs, neighbors, path, stats
from llm_wiki.pages import new_page


def _link(cfg, slug, target):
    """Append a [[target]] wiki-link to an existing page's body."""
    p = cfg.pages_dir / f"{slug}.md"
    fm, body = parse(p.read_text())
    p.write_text(dump(fm, body + f"\nSee [[{target}]].\n"))


def test_build_graph_nodes_and_link_edges(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="entity", title="A")
    new_page(wiki_cfg, type="concept", title="B")
    _link(wiki_cfg, "a", "b")
    g = build_graph(wiki_cfg)
    assert set(g.nodes) == {"a", "b"}
    assert g.has_edge("a", "b")
    assert g.nodes["a"]["type"] == "entity"


def test_build_graph_relations_and_skips_unknown_targets(wiki_cfg: WikiConfig):
    a = new_page(wiki_cfg, type="concept", title="A")
    new_page(wiki_cfg, type="concept", title="B")
    fm, body = parse(a.read_text())
    fm.relations = [{"predicate": "uses", "target": "b"}, {"predicate": "uses", "target": "ghost"}]
    a.write_text(dump(fm, body))
    g = build_graph(wiki_cfg)
    assert g.has_edge("a", "b")
    assert "uses" in g.edges["a", "b"]["predicates"]
    assert "ghost" not in g.nodes  # unknown target skipped


def test_neighbors_depth_and_filter(wiki_cfg: WikiConfig):
    for t in ("A", "B", "C"):
        new_page(wiki_cfg, type="concept", title=t)
    _link(wiki_cfg, "a", "b")
    _link(wiki_cfg, "b", "c")
    g = build_graph(wiki_cfg)
    d1 = {n["slug"] for n in neighbors(g, "a", depth=1)}
    d2 = {n["slug"] for n in neighbors(g, "a", depth=2)}
    assert d1 == {"b"}
    assert d2 == {"b", "c"}


def test_path_connected_and_disconnected(wiki_cfg: WikiConfig):
    for t in ("A", "B", "C"):
        new_page(wiki_cfg, type="concept", title=t)
    _link(wiki_cfg, "a", "b")
    g = build_graph(wiki_cfg)
    assert path(g, "a", "b") == ["a", "b"]
    assert path(g, "a", "c") is None


def test_hubs_orders_by_degree(wiki_cfg: WikiConfig):
    for t in ("Hub", "X", "Y"):
        new_page(wiki_cfg, type="concept", title=t)
    _link(wiki_cfg, "x", "hub")
    _link(wiki_cfg, "y", "hub")
    g = build_graph(wiki_cfg)
    top = hubs(g, limit=1)
    assert top[0]["slug"] == "hub"


def test_stats_counts(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="entity", title="A")
    new_page(wiki_cfg, type="concept", title="B")
    _link(wiki_cfg, "a", "b")
    s = stats(build_graph(wiki_cfg))
    assert s["nodes"] == 2
    assert s["edges"] == 1
    assert s["by_type"] == {"entity": 1, "concept": 1}


def test_multiple_predicates_between_same_pair_preserved(wiki_cfg: WikiConfig):
    a = new_page(wiki_cfg, type="concept", title="A")
    new_page(wiki_cfg, type="concept", title="B")
    fm, body = parse(a.read_text())
    fm.relations = [{"predicate": "uses", "target": "b"}]
    a.write_text(dump(fm, body + "\n[[b]]\n"))  # both a relation AND an inline link
    g = build_graph(wiki_cfg)
    assert {"links", "uses"} <= set(g.edges["a", "b"]["predicates"])
    # the "links" relationship is still discoverable under a predicate filter
    assert any(n["slug"] == "b" for n in neighbors(g, "a", predicate="links"))


def test_self_links_do_not_create_self_loops(wiki_cfg: WikiConfig):
    a = new_page(wiki_cfg, type="concept", title="A")
    fm, body = parse(a.read_text())
    a.write_text(dump(fm, body + "\n[[a]]\n"))
    g = build_graph(wiki_cfg)
    assert not g.has_edge("a", "a")
    assert stats(g)["edges"] == 0


def test_links_in_code_are_not_edges(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="A")
    new_page(wiki_cfg, type="concept", title="B")
    a = wiki_cfg.pages_dir / "a.md"
    fm, body = parse(a.read_text())
    # [[b]] only appears inside inline code — it must NOT create an edge.
    a.write_text(dump(fm, body + "\nUse the `[[b]]` token literally.\n"))
    g = build_graph(wiki_cfg)
    assert not g.has_edge("a", "b")


def test_export_json_and_dot(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="A")
    new_page(wiki_cfg, type="concept", title="B")
    _link(wiki_cfg, "a", "b")
    g = build_graph(wiki_cfg)
    data = json.loads(export(g, "json"))
    assert any(n["id"] == "a" for n in data["nodes"])
    dot = export(g, "dot")
    assert dot.startswith("digraph")
    assert '"a" -> "b"' in dot
