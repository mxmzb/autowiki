from llm_wiki.assets import load_template, page_template_name
from llm_wiki.frontmatter import PAGE_TYPES


def test_load_schema_template_nonempty():
    text = load_template("SCHEMA.md")
    assert "Maintainer Schema" in text


def test_every_page_type_has_a_template():
    for t in PAGE_TYPES:
        text = load_template(page_template_name(t))
        assert text.strip() != ""


def test_slash_command_templates_exist():
    for name in ("wiki-ingest", "wiki-query", "wiki-lint"):
        text = load_template(f"command_{name}.md")
        assert "llm-wiki" in text
