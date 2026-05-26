from pathlib import Path

import pytest

import llm_wiki.sources as sources
from llm_wiki.config import WikiConfig
from llm_wiki.pages import new_page
from llm_wiki.sources import add_source, ingested_ids, pending_sources, source_status


def test_add_local_file_copies_into_inbox(wiki_cfg: WikiConfig, tmp_path: Path):
    src = tmp_path / "notes.txt"
    src.write_text("hello world")
    sid = add_source(wiki_cfg, str(src))
    assert sid == "notes"
    matches = list(wiki_cfg.inbox_dir.glob("notes.*"))
    assert len(matches) == 1
    assert matches[0].read_text() == "hello world"


def test_add_local_is_idempotent(wiki_cfg: WikiConfig, tmp_path: Path):
    src = tmp_path / "notes.txt"
    src.write_text("hello")
    a = add_source(wiki_cfg, str(src))
    b = add_source(wiki_cfg, str(src))
    assert a == b
    assert len(list(wiki_cfg.inbox_dir.glob("notes.*"))) == 1


def test_add_url_fetches_content(wiki_cfg: WikiConfig, monkeypatch):
    class FakeResp:
        def read(self):
            return b"<html>page body</html>"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(sources.urllib.request, "urlopen", lambda *a, **k: FakeResp())
    sid = add_source(wiki_cfg, "https://example.com/article")
    f = wiki_cfg.inbox_dir / f"{sid}.html"
    assert f.exists()
    assert b"page body" in f.read_bytes()


def test_add_url_fetch_error_leaves_inbox_clean(wiki_cfg: WikiConfig, monkeypatch):
    def boom(*a, **k):
        raise sources.urllib.error.URLError("no network")

    monkeypatch.setattr(sources.urllib.request, "urlopen", boom)
    before = sorted(p.name for p in wiki_cfg.inbox_dir.iterdir())
    with pytest.raises(RuntimeError):
        add_source(wiki_cfg, "https://example.com/article")
    after = sorted(p.name for p in wiki_cfg.inbox_dir.iterdir())
    assert before == after  # nothing written on failure


def test_added_source_is_pending_until_referenced(wiki_cfg: WikiConfig, tmp_path: Path):
    src = tmp_path / "paper.txt"
    src.write_text("content")
    sid = add_source(wiki_cfg, str(src))
    assert sid in pending_sources(wiki_cfg)

    new_page(wiki_cfg, type="source-summary", title="Paper Summary", sources=[sid])
    assert sid not in pending_sources(wiki_cfg)
    assert sid in ingested_ids(wiki_cfg)


def test_source_status_marks_each(wiki_cfg: WikiConfig, tmp_path: Path):
    a = tmp_path / "a.txt"
    a.write_text("x")
    b = tmp_path / "b.txt"
    b.write_text("y")
    ida = add_source(wiki_cfg, str(a))
    idb = add_source(wiki_cfg, str(b))
    new_page(wiki_cfg, type="source-summary", title="A Summary", sources=[ida])
    marks = {d["id"]: d["ingested"] for d in source_status(wiki_cfg)}
    assert marks[ida] is True
    assert marks[idb] is False
    # .gitkeep is never counted as a source
    assert ".gitkeep" not in marks and "" not in marks


def test_add_source_unique_by_stem_across_extensions(wiki_cfg: WikiConfig, tmp_path: Path):
    a = tmp_path / "article.txt"
    a.write_text("one")
    b = tmp_path / "article.md"
    b.write_text("two")
    id1 = add_source(wiki_cfg, str(a))
    id2 = add_source(wiki_cfg, str(b))  # same derived id, different extension
    assert id1 == id2 == "article"
    assert len(list(wiki_cfg.inbox_dir.glob("article.*"))) == 1
