from pathlib import Path

from llm_wiki.config import CONFIG_NAME, load_config
from llm_wiki.managed_block import BEGIN
from llm_wiki.scaffold import init_wiki, project_root_of


def test_init_creates_expected_tree(project: Path):
    cfg, action = init_wiki(project, target="claude")
    assert action == "created"
    wiki = project / "wiki"
    for rel in ("inbox", "pages", "index.md", "log.md", "SCHEMA.md", CONFIG_NAME, ".gitignore"):
        assert (wiki / rel).exists(), rel
    assert (wiki / "inbox" / ".gitkeep").exists()
    assert (wiki / "pages" / ".gitkeep").exists()
    assert (wiki / ".gitignore").read_text().strip() == ".index/"
    assert "init | wiki initialized" in (wiki / "log.md").read_text()


def test_init_claude_target_writes_block_and_commands(project: Path):
    init_wiki(project, target="claude")
    assert BEGIN in (project / "CLAUDE.md").read_text()
    for name in ("wiki-ingest", "wiki-query", "wiki-lint"):
        assert (project / ".claude" / "commands" / f"{name}.md").exists()


def test_init_generic_target_writes_agents_md_no_commands(project: Path):
    init_wiki(project, target="generic")
    assert BEGIN in (project / "AGENTS.md").read_text()
    assert not (project / ".claude").exists()


def test_init_stores_target_in_config(project: Path):
    init_wiki(project, target="generic")
    assert load_config(project / "wiki").target == "generic"


def test_init_root_mode_places_files_at_root(project: Path):
    init_wiki(project, target="generic", root_mode=True)
    assert (project / CONFIG_NAME).exists()
    assert (project / "pages").exists()
    assert not (project / "wiki").exists()


def test_init_root_mode_preserves_existing_gitignore(project: Path):
    gi = project / ".gitignore"
    gi.write_text("node_modules/\n*.log\n")
    init_wiki(project, target="generic", root_mode=True)
    text = gi.read_text()
    assert "node_modules/" in text  # user rules preserved
    assert "*.log" in text
    assert ".index/" in text  # our rule added
    assert text.count(".index/") == 1  # not duplicated on content


def test_init_root_mode_gitignore_not_duplicated_on_reinit(project: Path):
    init_wiki(project, target="generic", root_mode=True)
    init_wiki(project, target="generic", root_mode=True, force=True)
    assert (project / ".gitignore").read_text().count(".index/") == 1


def test_project_root_of_uses_persisted_layout_not_dirname(tmp_path: Path):
    # A --root wiki whose project dir is literally named "wiki" must still be
    # treated as root layout (layout is persisted, not inferred from the name).
    proj = tmp_path / "wiki"
    proj.mkdir()
    cfg, _ = init_wiki(proj, target="generic", root_mode=True)
    root, root_mode = project_root_of(cfg)
    assert root_mode is True
    assert root == proj


def test_project_root_of_default_layout(project: Path):
    cfg, _ = init_wiki(project, target="generic")
    root, root_mode = project_root_of(cfg)
    assert root_mode is False
    assert root == project


def test_reinit_is_idempotent_and_preserves_log(project: Path):
    init_wiki(project, target="claude")
    log_before = (project / "wiki" / "log.md").read_text()
    (project / "CLAUDE.md").write_text(
        (project / "CLAUDE.md").read_text() + "\nUser added line.\n"
    )
    cfg, action = init_wiki(project, target="claude")
    assert action == "updated"
    assert (project / "wiki" / "log.md").read_text() == log_before  # log not reseeded
    assert "User added line." in (project / "CLAUDE.md").read_text()  # user content kept
