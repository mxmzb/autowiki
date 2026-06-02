import json
from pathlib import Path

from typer.testing import CliRunner

from autowiki.cli import app
from autowiki.hooks import hooks_installed

runner = CliRunner()


def _run(args, **kwargs):
    return runner.invoke(app, args, **kwargs)


def test_phase1_full_lifecycle(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()

    # init (claude + hooks)
    assert _run(["init", str(proj), "--target", "claude", "--hooks"]).exit_code == 0
    wiki = proj / "wiki"
    assert hooks_installed(proj)

    # add-source
    src = tmp_path / "paper.md"
    src.write_text("Transformers and the attention mechanism in large language models.")
    r = _run(["add-source", str(src), "--wiki", str(wiki)])
    assert r.exit_code == 0
    sid = r.stdout.strip()

    # new-page x2
    assert _run(
        ["new-page", "Transformers", "--type", "concept", "--summary",
         "attention-based models", "--sources", sid, "--wiki", str(wiki)]
    ).exit_code == 0
    assert _run(
        ["new-page", "Attention", "--type", "concept", "--summary",
         "the attention mechanism", "--wiki", str(wiki)]
    ).exit_code == 0

    # index + log
    assert _run(["index", "--wiki", str(wiki)]).exit_code == 0
    assert _run(["log", "ingest", "Transformers", "--wiki", str(wiki)]).exit_code == 0

    # search (json)
    r = _run(["search", "attention", "--json", "--wiki", str(wiki)])
    assert r.exit_code == 0
    hits = json.loads(r.stdout)
    assert {h["slug"] for h in hits} & {"transformers", "attention"}

    # status
    r = _run(["status", "--wiki", str(wiki)])
    assert r.exit_code == 0
    assert "Pages: 2" in r.stdout

    # doctor healthy
    assert _run(["doctor", "--wiki", str(wiki)]).exit_code == 0

    # lint --fix → no error-level issues
    assert _run(["lint", "--fix", "--wiki", str(wiki)]).exit_code == 0

    # upgrade, then doctor still healthy
    assert _run(["upgrade", "--wiki", str(wiki)]).exit_code == 0
    assert _run(["doctor", "--wiki", str(wiki)]).exit_code == 0
