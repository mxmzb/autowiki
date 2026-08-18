from autowiki.frontmatter import (
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
        related=["autowiki-pattern"],
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


def test_validate_flags_non_numeric_confidence_without_crashing():
    # A hand-edited page may put a non-numeric value in confidence; validate must
    # report it, not raise (validate backs lint and must never crash on bad input).
    fm = PageFrontmatter(title="X", type="note", created=today(), updated=today())
    fm.confidence = "high"  # type: ignore[assignment]
    errors = validate(fm)
    assert any("confidence" in e for e in errors)


def test_validate_accepts_custom_type_via_allowed_types():
    fm = PageFrontmatter(title="X", type="recipe", created=today(), updated=today())
    # Default rejects an unknown type...
    assert any("recipe" in e for e in validate(fm))
    # ...but passing allowed_types accepts it.
    assert validate(fm, allowed_types=(*PAGE_TYPES, "recipe")) == []


def test_parse_coerces_malformed_field_shapes():
    # Hand-edited pages may put a scalar where a list/str is expected. parse must
    # coerce to safe shapes so downstream consumers (lint/index/search) never crash.
    text = (
        "---\n"
        "title: X\n"
        "type: note\n"
        "created: '2026-01-01'\n"
        "updated: '2026-01-01'\n"
        "related: 7\n"      # scalar where a list is expected
        "tags: hello\n"     # bare string where a list is expected
        "summary: 123\n"    # number where a string is expected
        "---\nbody\n"
    )
    fm, _ = parse(text)
    assert fm.related == ["7"]
    assert fm.tags == ["hello"]
    assert fm.summary == "123"


def test_parse_coerces_relations_entries():
    text = (
        "---\n"
        "title: X\n"
        "type: note\n"
        "created: '2026-01-01'\n"
        "updated: '2026-01-01'\n"
        "relations:\n"
        "- predicate: uses\n"
        "  target: 7\n"      # non-str target -> coerced
        "- not-a-dict\n"     # malformed entry -> dropped
        "---\nbody\n"
    )
    fm, _ = parse(text)
    assert fm.relations == [{"predicate": "uses", "target": "7"}]


def test_evergreen_defaults_false_and_coerces_to_bool():
    fm = PageFrontmatter(title="X", type="note", created=today(), updated=today())
    assert fm.evergreen is False
    text = (
        "---\ntitle: X\ntype: note\ncreated: '2026-01-01'\nupdated: '2026-01-01'\n"
        "evergreen: maybe\n---\nbody\n"
    )
    parsed, _ = parse(text)
    assert parsed.evergreen is True


def test_round_trip_preserves_unknown_fields():
    """A downstream wiki may add its own frontmatter keys (SCHEMA.md invites it).
    Re-dumping a page must not silently drop them."""
    text = (
        "---\ntitle: X\ntype: note\ncreated: '2026-01-01'\nupdated: '2026-01-01'\n"
        "watch:\n- core/app/doctor.ts\n---\nbody\n"
    )
    fm, body = parse(text)
    assert "watch:" in dump(fm, body)
