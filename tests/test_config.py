from pathlib import Path

from llm_wiki.config import (
    CONFIG_NAME,
    WikiConfig,
    find_wiki_root,
    load_config,
    write_config,
)


def test_find_wiki_root_walks_up(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "pages").mkdir(parents=True)
    (wiki / CONFIG_NAME).write_text("[wiki]\nschema_version = 1\n")
    deep = wiki / "pages"
    assert find_wiki_root(deep) == wiki


def test_find_wiki_root_returns_none_when_absent(tmp_path: Path):
    assert find_wiki_root(tmp_path) is None


def test_config_round_trip(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    cfg = WikiConfig(root=wiki, target="generic", stale_days=30)
    write_config(cfg)
    loaded = load_config(wiki)
    assert loaded.target == "generic"
    assert loaded.stale_days == 30
    assert loaded.schema_version == 1


def test_config_path_helpers(tmp_path: Path):
    cfg = WikiConfig(root=tmp_path / "wiki")
    assert cfg.pages_dir.name == "pages"
    assert cfg.inbox_dir.name == "inbox"
    assert cfg.index_file.name == "index.md"
    assert cfg.log_file.name == "log.md"
