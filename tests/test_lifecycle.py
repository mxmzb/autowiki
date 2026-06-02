import datetime as dt

from autowiki.config import WikiConfig
from autowiki.frontmatter import PageFrontmatter, dump
from autowiki.lifecycle import retention, review, supersede
from autowiki.pages import load_page, new_page

NOW = dt.date(2026, 1, 1)


def _fm(**kw):
    base = dict(title="X", type="note", created="2025-01-01", updated="2025-01-01")
    base.update(kw)
    return PageFrontmatter(**base)


def test_evergreen_never_decays():
    assert retention(_fm(evergreen=True, updated="2000-01-01"), NOW) == 1.0


def test_working_decays_faster_than_semantic():
    old = "2025-06-01"
    assert retention(_fm(tier="working", updated=old), NOW) < retention(
        _fm(tier="semantic", updated=old), NOW
    )


def test_higher_confidence_decays_slower():
    lo = _fm(tier="semantic", confidence=0.1, updated="2025-06-01")
    hi = _fm(tier="semantic", confidence=0.9, updated="2025-06-01")
    assert retention(hi, NOW) > retention(lo, NOW)


def test_review_lists_decayed_and_omits_evergreen(wiki_cfg: WikiConfig):
    p1 = new_page(wiki_cfg, type="note", title="Stale", tier="working")
    fm, body = load_page(p1)
    fm.updated = "2020-01-01"
    p1.write_text(dump(fm, body))
    p2 = new_page(wiki_cfg, type="note", title="Timeless", evergreen=True)
    fm2, body2 = load_page(p2)
    fm2.updated = "2020-01-01"
    p2.write_text(dump(fm2, body2))

    slugs = {r["slug"] for r in review(wiki_cfg)}
    assert "stale" in slugs
    assert "timeless" not in slugs


def test_supersede_wires_both_sides(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Old Way")
    new_page(wiki_cfg, type="concept", title="New Way")
    supersede(wiki_cfg, "old-way", "new-way")
    old_fm, _ = load_page(wiki_cfg.pages_dir / "old-way.md")
    new_fm, _ = load_page(wiki_cfg.pages_dir / "new-way.md")
    assert old_fm.status == "superseded"
    assert "new-way" in old_fm.superseded_by
    assert "old-way" in new_fm.supersedes


def test_supersede_idempotent(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="A")
    new_page(wiki_cfg, type="concept", title="B")
    supersede(wiki_cfg, "a", "b")
    supersede(wiki_cfg, "a", "b")
    old_fm, _ = load_page(wiki_cfg.pages_dir / "a.md")
    assert old_fm.superseded_by == ["b"]


def test_supersede_missing_page_raises(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Only")
    import pytest

    with pytest.raises(FileNotFoundError):
        supersede(wiki_cfg, "only", "ghost")


def test_retention_clamped_and_safe_on_bad_confidence():
    # negative / >1 / boolean confidence must never crash and must stay in (0, 1]
    for c in (-0.5, -1.0, 5.0, True):
        r = retention(_fm(confidence=c, updated="2025-06-01"), NOW)
        assert 0.0 < r <= 1.0


def test_review_survives_bad_confidence_page(wiki_cfg: WikiConfig):
    p = new_page(wiki_cfg, type="note", title="Bad")
    fm, body = load_page(p)
    fm.confidence = -0.5  # type: ignore[assignment]
    p.write_text(dump(fm, body))
    review(wiki_cfg)  # must not raise


def test_supersede_self_raises(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="A")
    import pytest

    with pytest.raises(ValueError):
        supersede(wiki_cfg, "a", "a")
