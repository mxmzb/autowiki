from llm_wiki.catalog import build_index, index_is_current, write_index
from llm_wiki.config import WikiConfig
from llm_wiki.pages import new_page


def test_empty_wiki_index_is_seed_and_current(wiki_cfg: WikiConfig):
    assert index_is_current(wiki_cfg)
    assert "_No pages yet._" in build_index(wiki_cfg)


def test_adding_page_makes_index_stale_until_written(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="entity", title="Andrej Karpathy", summary="ML researcher")
    assert not index_is_current(wiki_cfg)
    write_index(wiki_cfg)
    assert index_is_current(wiki_cfg)
    text = wiki_cfg.index_file.read_text()
    assert "## Entity" in text
    assert "[[andrej-karpathy]] — ML researcher" in text


def test_index_grouping_is_deterministic(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="note", title="Zeta")
    new_page(wiki_cfg, type="entity", title="Beta")
    new_page(wiki_cfg, type="entity", title="Alpha")
    out = build_index(wiki_cfg)
    # Entity group before Note (PAGE_TYPES order); titles alphabetized within a group.
    assert out.index("## Entity") < out.index("## Note")
    assert out.index("[[alpha]]") < out.index("[[beta]]")
