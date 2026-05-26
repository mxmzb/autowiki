from llm_wiki.catalog import write_index
from llm_wiki.config import WikiConfig
from llm_wiki.frontmatter import PageFrontmatter, dump, parse, today
from llm_wiki.lint import fix, run_lint
from llm_wiki.pages import new_page


def _codes(issues):
    return {i.code for i in issues}


def test_clean_wiki_has_no_error_level_issues(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="entity", title="A", summary="x")
    new_page(wiki_cfg, type="note", title="B", summary="y")
    write_index(wiki_cfg)
    errors = [i for i in run_lint(wiki_cfg) if i.level == "error"]
    assert errors == []


def test_bad_frontmatter_does_not_crash(wiki_cfg: WikiConfig):
    (wiki_cfg.pages_dir / "broken.md").write_text("no frontmatter here\n")
    assert "bad_frontmatter" in _codes(run_lint(wiki_cfg))


def test_broken_link_detected(wiki_cfg: WikiConfig):
    p = new_page(wiki_cfg, type="note", title="Has Link")
    fm, body = parse(p.read_text())
    p.write_text(dump(fm, body + "\nSee [[nonexistent-page]].\n"))
    assert "broken_link" in _codes(run_lint(wiki_cfg))


def test_duplicate_slug_detected(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="note", title="Dup", slug="dup")
    (wiki_cfg.pages_dir / "dup-copy.md").write_text(
        dump(
            PageFrontmatter(title="Dup2", type="note", created=today(), updated=today(), slug="dup"),
            "body",
        )
    )
    assert "duplicate_slug" in _codes(run_lint(wiki_cfg))


def test_missing_source_detected(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="source-summary", title="S", sources=["ghost"])
    assert "missing_source" in _codes(run_lint(wiki_cfg))


def test_orphan_detected(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="note", title="Lonely")
    assert "orphan" in _codes(run_lint(wiki_cfg))


def test_stale_review_by_detected(wiki_cfg: WikiConfig):
    p = new_page(wiki_cfg, type="note", title="Old")
    fm, body = parse(p.read_text())
    fm.review_by = "2000-01-01"
    p.write_text(dump(fm, body))
    assert "stale" in _codes(run_lint(wiki_cfg))


def test_index_stale_detected_and_fixed(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="note", title="New")
    assert "index_stale" in _codes(run_lint(wiki_cfg))
    fix(wiki_cfg)
    assert "index_stale" not in _codes(run_lint(wiki_cfg))


def test_contradiction_is_info_level(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="A")  # slug "a"
    p = new_page(wiki_cfg, type="concept", title="B")
    fm, body = parse(p.read_text())
    fm.contradicts = ["a"]
    p.write_text(dump(fm, body))
    assert any(i.code == "contradiction" and i.level == "info" for i in run_lint(wiki_cfg))


def test_lint_does_not_crash_on_shape_malformed_page(wiki_cfg: WikiConfig):
    # YAML-valid but wrong-shaped frontmatter must not crash lint.
    (wiki_cfg.pages_dir / "weird.md").write_text(
        "---\ntitle: Weird\ntype: note\ncreated: '2026-01-01'\n"
        "updated: '2026-01-01'\nrelated: 7\nsummary: 99\n---\nbody\n"
    )
    issues = run_lint(wiki_cfg)  # must not raise
    # the scalar `related: 7` is coerced to ["7"], surfacing as a broken link
    assert any(i.code == "broken_link" for i in issues)


def test_broken_relations_target_detected(wiki_cfg: WikiConfig):
    p = new_page(wiki_cfg, type="concept", title="A")
    fm, body = parse(p.read_text())
    fm.relations = [{"predicate": "uses", "target": "ghost"}]
    p.write_text(dump(fm, body))
    assert "broken_link" in _codes(run_lint(wiki_cfg))


def test_resolving_relations_target_has_no_broken_link(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Target")  # slug "target"
    p = new_page(wiki_cfg, type="concept", title="A")
    fm, body = parse(p.read_text())
    fm.relations = [{"predicate": "uses", "target": "target"}]
    p.write_text(dump(fm, body))
    assert not any(i.code == "broken_link" for i in run_lint(wiki_cfg))
