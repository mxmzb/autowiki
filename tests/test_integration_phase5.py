import json
from pathlib import Path

from typer.testing import CliRunner

from llm_wiki.cli import app
from llm_wiki.hooks import run_hook

runner = CliRunner()


def _run(args):
    return runner.invoke(app, args)


def test_phase5_automation(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    assert _run(["init", str(proj), "--target", "generic"]).exit_code == 0
    wiki = proj / "wiki"

    f1 = tmp_path / "one.txt"
    f1.write_text("alpha content")
    f2 = tmp_path / "two.txt"
    f2.write_text("beta content")
    id1 = _run(["add-source", str(f1), "--wiki", str(wiki)]).stdout.strip()
    _run(["add-source", str(f2), "--wiki", str(wiki)])

    # both sources pending
    pending = {d["id"] for d in json.loads(_run(["sources", "--pending", "--json", "--wiki", str(wiki)]).stdout)}
    assert pending == {"one", "two"}

    # ingest one of them
    _run(["new-page", "One Summary", "--type", "source-summary", "--sources", id1, "--wiki", str(wiki)])
    pending = {d["id"] for d in json.loads(_run(["sources", "--pending", "--json", "--wiki", str(wiki)]).stdout)}
    assert pending == {"two"}

    # maintain reports the remaining pending source
    assert "pending sources: 1" in _run(["maintain", "--wiki", str(wiki)]).stdout

    # the SessionStart hook surfaces it to the agent
    _code, msg = run_hook("session-start", json.dumps({"cwd": str(wiki)}))
    assert "awaiting ingest" in msg

    # quality runs
    assert _run(["quality", "--wiki", str(wiki)]).exit_code == 0
