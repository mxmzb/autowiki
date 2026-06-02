import pytest

from autowiki.config import WikiConfig
from autowiki.pages import list_page_paths, load_page, new_page, slugify


def test_slugify():
    assert slugify("Andrej Karpathy!") == "andrej-karpathy"
    assert slugify("  C++  Templates  ") == "c-templates"
    assert slugify("already-a-slug") == "already-a-slug"


def test_new_page_writes_valid_frontmatter(wiki_cfg: WikiConfig):
    path = new_page(
        wiki_cfg,
        type="entity",
        title="Andrej Karpathy",
        summary="ML researcher",
        tags=["ml"],
        sources=["src1"],
    )
    assert path.name == "andrej-karpathy.md"
    fm, _ = load_page(path)
    assert fm.title == "Andrej Karpathy"
    assert fm.type == "entity"
    assert fm.slug == "andrej-karpathy"
    assert fm.summary == "ML researcher"
    assert fm.tags == ["ml"]
    assert fm.sources == ["src1"]
    assert fm.created and fm.updated


def test_new_page_duplicate_slug_raises(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="note", title="Same Title")
    with pytest.raises(FileExistsError):
        new_page(wiki_cfg, type="note", title="Same Title")


def test_new_page_unknown_type_raises(wiki_cfg: WikiConfig):
    with pytest.raises(ValueError):
        new_page(wiki_cfg, type="bogus", title="X")


def test_new_page_custom_type_allowed(wiki_cfg: WikiConfig):
    wiki_cfg.extra_types.append("recipe")
    path = new_page(wiki_cfg, type="recipe", title="Pancakes")
    fm, _ = load_page(path)
    assert fm.type == "recipe"


def test_list_page_paths(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="note", title="A")
    new_page(wiki_cfg, type="note", title="B")
    assert len(list_page_paths(wiki_cfg)) == 2


def test_entity_template_uses_references_not_sources(wiki_cfg: WikiConfig):
    # The body section is external references; "Sources" is reserved for the
    # frontmatter provenance field, so the heading must not reuse that word.
    body = new_page(wiki_cfg, type="entity", title="X").read_text()
    assert "## References" in body
    assert "## Sources" not in body


def test_concept_template_uses_references_not_sources(wiki_cfg: WikiConfig):
    body = new_page(wiki_cfg, type="concept", title="Y").read_text()
    assert "## References" in body
    assert "## Sources" not in body
