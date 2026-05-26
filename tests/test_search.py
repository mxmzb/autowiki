from llm_wiki.config import WikiConfig
from llm_wiki.pages import new_page
from llm_wiki.search import search


def test_search_ranks_matching_page_first(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="entity", title="Andrej Karpathy", summary="neural networks researcher")
    new_page(wiki_cfg, type="concept", title="Bicycle Maintenance", summary="fixing bikes")
    hits = search(wiki_cfg, "neural networks")
    assert hits
    assert hits[0].slug == "andrej-karpathy"


def test_search_no_match_returns_empty(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="note", title="Something", summary="about cooking")
    assert search(wiki_cfg, "quantum chromodynamics") == []


def test_search_empty_query_returns_empty(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="note", title="X", summary="hello")
    assert search(wiki_cfg, "   ") == []


def test_search_empty_wiki_returns_empty(wiki_cfg: WikiConfig):
    assert search(wiki_cfg, "anything") == []


def test_search_type_filter(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="entity", title="Carbon", summary="an element")
    new_page(wiki_cfg, type="concept", title="Carbon Cycle", summary="carbon through earth")
    hits = search(wiki_cfg, "carbon", type="concept")
    assert hits
    assert all(h.slug == "carbon-cycle" for h in hits)
