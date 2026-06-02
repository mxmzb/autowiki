from typer.testing import CliRunner

from autowiki.cli import app
from autowiki.config import WikiConfig
from autowiki.pages import new_page

runner = CliRunner()


def test_maintain_rebuilds_index_and_reports(wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="note", title="A", summary="x")
    r = runner.invoke(app, ["maintain", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert "Maintenance report" in r.stdout
    assert "lint:" in r.stdout
    assert "pending sources:" in r.stdout
    # the rebuild made the index list the page
    assert "[[a]]" in wiki_cfg.index_file.read_text()
