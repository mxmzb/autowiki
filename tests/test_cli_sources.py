from pathlib import Path

from typer.testing import CliRunner

from llm_wiki.cli import app
from llm_wiki.config import WikiConfig
from llm_wiki.pages import new_page
from llm_wiki.sources import add_source

runner = CliRunner()


def test_sources_command_marks_pending_and_ingested(wiki_cfg: WikiConfig, tmp_path: Path):
    a = tmp_path / "a.txt"
    a.write_text("x")
    b = tmp_path / "b.txt"
    b.write_text("y")
    ida = add_source(wiki_cfg, str(a))
    add_source(wiki_cfg, str(b))
    new_page(wiki_cfg, type="source-summary", title="A Summary", sources=[ida])

    r = runner.invoke(app, ["sources", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert "ingested" in r.stdout
    assert "pending" in r.stdout

    r = runner.invoke(app, ["sources", "--pending", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert "b" in r.stdout
    assert "a\n" not in r.stdout  # the ingested one is omitted in --pending mode


def test_new_source_command_creates_empty(wiki_cfg: WikiConfig):
    r = runner.invoke(app, ["new-source", "My Note", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert (wiki_cfg.inbox_dir / "my-note.md").exists()
    assert (wiki_cfg.inbox_dir / "my-note.md").read_text() == ""


def test_new_source_command_reads_stdin(wiki_cfg: WikiConfig):
    r = runner.invoke(
        app, ["new-source", "Piped", "--wiki", str(wiki_cfg.root)], input="pasted content"
    )
    assert r.exit_code == 0
    assert (wiki_cfg.inbox_dir / "piped.md").read_text() == "pasted content"


def test_status_reports_pending_sources(wiki_cfg: WikiConfig, tmp_path: Path):
    src = tmp_path / "notes.txt"
    src.write_text("hi")
    add_source(wiki_cfg, str(src))
    r = runner.invoke(app, ["status", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert "Pending sources: 1" in r.stdout
