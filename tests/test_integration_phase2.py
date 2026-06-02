import json
from pathlib import Path

from typer.testing import CliRunner

from autowiki.cli import app
from autowiki.frontmatter import dump, parse

runner = CliRunner()


def _run(args):
    return runner.invoke(app, args)


def test_phase2_graph_lifecycle(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    assert _run(["init", str(proj), "--target", "generic"]).exit_code == 0
    wiki = proj / "wiki"

    assert _run(["new-page", "PyTorch", "--type", "entity", "--summary", "an ML framework",
                 "--wiki", str(wiki)]).exit_code == 0
    assert _run(["new-page", "Transformers", "--type", "concept", "--summary", "attention models",
                 "--wiki", str(wiki)]).exit_code == 0

    # transformers --uses--> pytorch, plus an inline link
    tp = wiki / "pages" / "transformers.md"
    fm, body = parse(tp.read_text())
    fm.relations = [{"predicate": "uses", "target": "pytorch"}]
    tp.write_text(dump(fm, body + "\nBuilt on [[pytorch]].\n"))

    # neighbors reflects the edge
    r = _run(["graph", "neighbors", "transformers", "--json", "--wiki", str(wiki)])
    assert r.exit_code == 0
    assert any(n["slug"] == "pytorch" for n in json.loads(r.stdout))

    # path connects them
    r = _run(["graph", "path", "transformers", "pytorch", "--wiki", str(wiki)])
    assert r.exit_code == 0
    assert "pytorch" in r.stdout

    # hubs returns data
    assert _run(["graph", "hubs", "--json", "--wiki", str(wiki)]).exit_code == 0

    # a broken relations target is reported by lint (exit 2)
    fm, body = parse(tp.read_text())
    fm.relations = [{"predicate": "uses", "target": "ghost"}]
    tp.write_text(dump(fm, body))
    r = _run(["lint", "--json", "--wiki", str(wiki)])
    assert r.exit_code == 2
    assert any(i["code"] == "broken_link" for i in json.loads(r.stdout))
