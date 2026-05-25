from llm_wiki.frontmatter import (
    PAGE_TYPES,
    PageFrontmatter,
    dump,
    parse,
    today,
    validate,
)


def test_full_schema_defaults_present():
    fm = PageFrontmatter(title="X", type="entity", created="2026-05-25", updated="2026-05-25")
    assert fm.status == "active"
    assert fm.tier == "semantic"
    assert fm.confidence is None
    assert fm.tags == [] and fm.related == [] and fm.entities == []


def test_dump_then_parse_round_trip():
    fm = PageFrontmatter(
        title="Andrej Karpathy",
        type="entity",
        created="2026-05-25",
        updated="2026-05-25",
        slug="andrej-karpathy",
        summary="ML researcher",
        tags=["ml", "people"],
        related=["llm-wiki-pattern"],
    )
    text = dump(fm, "Body paragraph.\n")
    parsed, body = parse(text)
    assert parsed == fm
    assert body.strip() == "Body paragraph."


def test_parse_tolerates_unknown_fields():
    text = "---\ntitle: X\ntype: note\ncreated: '2026-05-25'\nupdated: '2026-05-25'\nbogus: 1\n---\nbody\n"
    fm, _ = parse(text)
    assert fm.title == "X"


def test_validate_reports_missing_required_and_bad_enums():
    fm = PageFrontmatter(title="", type="widget", created="", updated="2026-05-25")
    errors = validate(fm)
    assert any("title" in e for e in errors)
    assert any("created" in e for e in errors)
    assert any("widget" in e for e in errors)


def test_validate_clean_page_has_no_errors():
    fm = PageFrontmatter(title="X", type="concept", created=today(), updated=today())
    assert validate(fm) == []


def test_page_types_constant():
    assert "source-summary" in PAGE_TYPES and "note" in PAGE_TYPES
