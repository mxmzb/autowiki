from pathlib import Path

import pytest

import llm_wiki.sources as sources
from llm_wiki.config import WikiConfig
from llm_wiki.sources import add_source


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
