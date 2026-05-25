from pathlib import Path

from llm_wiki.managed_block import BEGIN, END, render_block, upsert_block


def test_render_block_claude_uses_import():
    block = render_block("claude", "wiki/")
    assert "@wiki/SCHEMA.md" in block
    assert BEGIN in block and END in block


def test_render_block_generic_uses_plain_pointer():
    block = render_block("generic", "wiki/")
    assert "@wiki/SCHEMA.md" not in block
    assert "wiki/SCHEMA.md" in block


def test_upsert_creates_file_and_preserves_existing_content(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("# My Project\n\nExisting notes.\n")
    upsert_block(f, render_block("claude", "wiki/"))
    text = f.read_text()
    assert "# My Project" in text
    assert "Existing notes." in text
    assert BEGIN in text


def test_upsert_is_idempotent(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    block = render_block("claude", "wiki/")
    upsert_block(f, block)
    first = f.read_text()
    upsert_block(f, block)
    assert f.read_text() == first


def test_upsert_replaces_old_block(tmp_path: Path):
    f = tmp_path / "AGENTS.md"
    upsert_block(f, render_block("generic", "wiki/"))
    upsert_block(f, render_block("generic", "docs/"))
    text = f.read_text()
    assert text.count(BEGIN) == 1
    assert "docs/SCHEMA.md" in text
