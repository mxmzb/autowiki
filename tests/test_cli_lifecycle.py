from pathlib import Path

from typer.testing import CliRunner

from autowiki.cli import app
from autowiki.config import WikiConfig
from autowiki.frontmatter import dump, parse
from autowiki.pages import load_page, new_page

runner = CliRunner()


def test_new_page_lifecycle_flags_persist(wiki_cfg: WikiConfig):
    r = runner.invoke(
        app,
        ["new-page", "Timeless", "--type", "concept", "--tier", "procedural",
         "--confidence", "0.9", "--evergreen", "--wiki", str(wiki_cfg.root)],
    )
    assert r.exit_code == 0
    fm, _ = load_page(wiki_cfg.pages_dir / "timeless.md")
    assert fm.evergreen is True
    assert fm.tier == "procedural"
    assert fm.confidence == 0.9


def test_supersede_command(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Old")
    new_page(wiki_cfg, type="concept", title="New")
    r = runner.invoke(app, ["supersede", "old", "new", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    fm, _ = load_page(wiki_cfg.pages_dir / "old.md")
    assert fm.status == "superseded"


def test_supersede_missing_page_exits_1(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Only")
    r = runner.invoke(app, ["supersede", "only", "ghost", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 1


def test_supersede_self_exits_1(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="A")
    r = runner.invoke(app, ["supersede", "a", "a", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 1


def test_review_lists_overdue(wiki_cfg: WikiConfig):
    p = new_page(wiki_cfg, type="note", title="Stale", tier="working")
    fm, body = parse(p.read_text())
    fm.review_by = "2000-01-01"
    p.write_text(dump(fm, body))
    r = runner.invoke(app, ["review", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert "stale" in r.stdout


def test_review_nothing_due(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Fresh", evergreen=True)
    r = runner.invoke(app, ["review", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert "Nothing needs review" in r.stdout


def test_status_shows_lifecycle_breakdown(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="A", tier="procedural")
    r = runner.invoke(app, ["status", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert "Tiers:" in r.stdout
    assert "procedural" in r.stdout
    assert "Review due:" in r.stdout
