from autowiki.config import WikiConfig
from autowiki.frontmatter import PageFrontmatter, today
from autowiki.pages import new_page
from autowiki.quality import quality_report, quality_score


def test_bare_page_scores_low():
    fm = PageFrontmatter(title="X", type="note", created=today(), updated=today())
    score, missing = quality_score(fm, "")
    assert score < 0.5
    assert "summary" in missing
    assert "sources" in missing


def test_rich_page_scores_high():
    fm = PageFrontmatter(
        title="X",
        type="concept",
        created=today(),
        updated=today(),
        summary="a good one-line summary",
        sources=["s1"],
        tags=["t"],
        confidence=0.8,
        related=["other"],
    )
    score, missing = quality_score(fm, "word " * 40)
    assert score >= 0.9
    assert missing == []


def test_quality_report_orders_weakest_first(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Rich", summary="full", sources=["s"], tags=["a"], confidence=0.9)
    new_page(wiki_cfg, type="note", title="Bare")
    report = quality_report(wiki_cfg)
    assert report[0]["slug"] == "bare"
    assert report[0]["score"] <= report[-1]["score"]
