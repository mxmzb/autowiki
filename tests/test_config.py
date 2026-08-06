from pathlib import Path

import pytest

from autowiki.config import (
    CONFIG_NAME,
    WikiConfig,
    find_wiki_root,
    load_config,
    write_config,
)


def test_new_config_defaults_to_alongside_pr(tmp_path: Path):
    assert WikiConfig(root=tmp_path / "wiki").wiki_update_mode == "alongside_pr"


def test_legacy_config_without_mode_loads_as_after_merge(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / CONFIG_NAME).write_text("[wiki]\nschema_version = 1\n")
    assert load_config(wiki).wiki_update_mode == "after_merge"


def test_wiki_update_mode_round_trip(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    write_config(WikiConfig(root=wiki, wiki_update_mode="after-merge"))
    assert load_config(wiki).wiki_update_mode == "after_merge"
    assert 'wiki_update_mode = "after_merge"' in (wiki / CONFIG_NAME).read_text()


def test_invalid_wiki_update_mode_fails_loudly(tmp_path: Path):
    with pytest.raises(ValueError, match="alongside_pr.*after_merge"):
        WikiConfig(root=tmp_path / "wiki", wiki_update_mode="sometimes")


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


def test_extra_types_round_trip_and_allowed_types(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    cfg = WikiConfig(root=wiki, extra_types=["recipe", "meeting"])
    write_config(cfg)
    loaded = load_config(wiki)
    assert loaded.extra_types == ["recipe", "meeting"]
    # allowed_types = built-in PAGE_TYPES plus the custom ones
    assert "entity" in loaded.allowed_types
    assert "recipe" in loaded.allowed_types and "meeting" in loaded.allowed_types


def test_extra_types_defaults_empty(tmp_path: Path):
    cfg = WikiConfig(root=tmp_path / "wiki")
    assert cfg.extra_types == []
    assert "recipe" not in cfg.allowed_types


def test_find_wiki_root_finds_wiki_subdir_from_project_root(tmp_path: Path):
    # Default layout: config lives in a wiki/ subdir; running a command from the
    # project root must still locate it (not only by walking up).
    proj = tmp_path / "proj"
    (proj / "wiki").mkdir(parents=True)
    (proj / "wiki" / CONFIG_NAME).write_text("[wiki]\nschema_version = 1\n")
    assert find_wiki_root(proj) == proj / "wiki"
