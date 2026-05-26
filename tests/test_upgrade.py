from llm_wiki.assets import load_template
from llm_wiki.config import SCHEMA_VERSION, WikiConfig, load_config, write_config
from llm_wiki.pages import load_page, new_page
from llm_wiki.upgrade import upgrade


def test_upgrade_restores_schema_template(wiki_cfg: WikiConfig):
    wiki_cfg.schema_file.write_text("I hand-edited this\n")
    upgrade(wiki_cfg)
    assert wiki_cfg.schema_file.read_text() == load_template("SCHEMA.md")


def test_upgrade_preserves_config_customizations(wiki_cfg: WikiConfig):
    wiki_cfg.extra_types = ["recipe"]
    wiki_cfg.stale_days = 30
    write_config(wiki_cfg)
    upgrade(wiki_cfg)
    reloaded = load_config(wiki_cfg.root)
    assert reloaded.extra_types == ["recipe"]
    assert reloaded.stale_days == 30
    assert reloaded.schema_version == SCHEMA_VERSION


def test_upgrade_does_not_touch_content(wiki_cfg: WikiConfig):
    p = new_page(wiki_cfg, type="note", title="Keep Me", summary="body matters")
    (wiki_cfg.inbox_dir / "raw.txt").write_text("RAW")
    log_before = wiki_cfg.log_file.read_text()

    upgrade(wiki_cfg)

    assert (wiki_cfg.inbox_dir / "raw.txt").read_text() == "RAW"
    assert wiki_cfg.log_file.read_text() == log_before
    fm, _ = load_page(p)
    assert fm.title == "Keep Me"
    assert fm.summary == "body matters"
