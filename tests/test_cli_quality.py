from typer.testing import CliRunner

from llm_wiki.cli import app
from llm_wiki.config import WikiConfig
from llm_wiki.pages import new_page

runner = CliRunner()


def test_quality_command_lists_weakest(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="note", title="Bare")
    r = runner.invoke(app, ["quality", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert "bare" in r.stdout
    assert "missing" in r.stdout
