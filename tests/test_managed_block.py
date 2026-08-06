from pathlib import Path

from autowiki.managed_block import BEGIN, END, render_block, upsert_block


def test_render_block_claude_uses_import():
    block = render_block("claude", "wiki/", "after_merge")
    assert "@wiki/SCHEMA.md" in block
    assert BEGIN in block and END in block


def test_render_block_generic_uses_plain_pointer():
    block = render_block("generic", "wiki/", "after_merge")
    assert "@wiki/SCHEMA.md" not in block
    assert "wiki/SCHEMA.md" in block


def test_upsert_creates_file_and_preserves_existing_content(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("# My Project\n\nExisting notes.\n")
    upsert_block(f, render_block("claude", "wiki/", "after_merge"))
    text = f.read_text()
    assert "# My Project" in text
    assert "Existing notes." in text
    assert BEGIN in text


def test_upsert_is_idempotent(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    block = render_block("claude", "wiki/", "after_merge")
    upsert_block(f, block)
    first = f.read_text()
    upsert_block(f, block)
    assert f.read_text() == first


def test_upsert_replaces_old_block(tmp_path: Path):
    f = tmp_path / "AGENTS.md"
    upsert_block(f, render_block("generic", "wiki/", "after_merge"))
    upsert_block(f, render_block("generic", "docs/", "after_merge"))
    text = f.read_text()
    assert text.count(BEGIN) == 1
    assert "docs/SCHEMA.md" in text


def test_render_block_root_mode_has_no_wiki_prefix_or_double_slash():
    # Root mode (wiki_rel="") places the wiki at the repo root: refs must be
    # bare (e.g. @SCHEMA.md), with no "wiki/" prefix and no "//" artifacts.
    block = render_block("claude", "", "after_merge")
    assert "@SCHEMA.md" in block
    assert "wiki/" not in block
    assert "//" not in block


def test_render_block_alongside_pr_uses_same_pr_workflow():
    block = render_block("generic", "wiki/", "alongside_pr")
    assert "immediately before creating the PR" in block
    assert "create a draft PR" in block
    assert "same branch" in block
    assert "Do not suggest a separate wiki ingest" in block
    assert "Always suggest on a merge" not in block


def test_render_block_after_merge_uses_separate_workflow():
    block = render_block("generic", "wiki/", "after_merge")
    assert "Always suggest on a merge" in block
    assert "create a draft PR" not in block
    assert "same branch" not in block
