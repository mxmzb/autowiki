from autowiki.assets import load_template
from autowiki.config import SCHEMA_VERSION, WikiConfig, load_config, write_config
from autowiki.pages import load_page, new_page
from autowiki.upgrade import upgrade


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


def test_upgrade_and_doctor_work_in_root_layout(tmp_path):
    from autowiki.doctor import doctor
    from autowiki.scaffold import init_wiki

    proj = tmp_path / "kb"
    proj.mkdir()
    cfg, _ = init_wiki(proj, target="generic", root_mode=True)
    upgrade(cfg)
    # managed block refreshed at the project root, not a parent dir
    assert (proj / "AGENTS.md").exists()
    findings = doctor(cfg)
    assert not any(level == "error" for level, _ in findings)
    assert any("managed block present" in msg for _level, msg in findings)


def test_upgrade_ensures_index_is_gitignored(wiki_cfg: WikiConfig):
    # Simulate a pre-Phase-3 wiki whose .gitignore lacks the .index/ line.
    gi = wiki_cfg.root / ".gitignore"
    gi.write_text("")
    upgrade(wiki_cfg)
    assert ".index/" in gi.read_text()
