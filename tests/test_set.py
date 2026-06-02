import pytest
from typer.testing import CliRunner

from autowiki.cli import app
from autowiki.config import WikiConfig
from autowiki.frontmatter import dump, parse, today
from autowiki.pages import new_page, set_page_fields

runner = CliRunner()


def _backdate(cfg, slug):
    p = cfg.pages_dir / f"{slug}.md"
    fm, body = parse(p.read_text())
    fm.updated = "2000-01-01"
    p.write_text(dump(fm, body))


def _reload(cfg, slug):
    return parse((cfg.pages_dir / f"{slug}.md").read_text())[0]


def test_set_confidence_updates_field_and_bumps_updated(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="A")
    _backdate(wiki_cfg, "a")
    set_page_fields(wiki_cfg, "a", confidence=0.8)
    fm = _reload(wiki_cfg, "a")
    assert fm.confidence == 0.8
    assert fm.updated == today()  # auto-bumped


def test_set_add_source_appends_without_duplicates(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="source-summary", title="S", sources=["a"])
    set_page_fields(wiki_cfg, "s", add_sources=["a", "b"])
    fm = _reload(wiki_cfg, "s")
    assert fm.sources == ["a", "b"]


def test_set_invalid_confidence_raises_and_does_not_write(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="A")
    _backdate(wiki_cfg, "a")
    with pytest.raises(ValueError):
        set_page_fields(wiki_cfg, "a", confidence=1.5)
    # nothing was written: updated stayed backdated
    assert _reload(wiki_cfg, "a").updated == "2000-01-01"


def test_set_unknown_slug_raises(wiki_cfg: WikiConfig):
    with pytest.raises(FileNotFoundError):
        set_page_fields(wiki_cfg, "ghost", confidence=0.5)


def test_set_evergreen_flag(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="note", title="A")
    set_page_fields(wiki_cfg, "a", evergreen=True)
    assert _reload(wiki_cfg, "a").evergreen is True


def test_cli_set_command(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    runner.invoke(app, ["init", str(proj), "--target", "generic"])
    wiki = proj / "wiki"
    runner.invoke(app, ["new-page", "A", "--type", "concept", "--wiki", str(wiki)])
    r = runner.invoke(app, ["set", "a", "--confidence", "0.9", "--tier", "procedural", "--wiki", str(wiki)])
    assert r.exit_code == 0, r.stdout
    fm, _ = parse((wiki / "pages" / "a.md").read_text())
    assert fm.confidence == 0.9
    assert fm.tier == "procedural"


def test_cli_set_rejects_invalid(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    runner.invoke(app, ["init", str(proj), "--target", "generic"])
    wiki = proj / "wiki"
    runner.invoke(app, ["new-page", "A", "--type", "concept", "--wiki", str(wiki)])
    r = runner.invoke(app, ["set", "a", "--tier", "bogus", "--wiki", str(wiki)])
    assert r.exit_code == 1
