from pathlib import Path

from typer.testing import CliRunner

from autowiki.cli import app
from autowiki.frontmatter import dump, parse

runner = CliRunner()


def _run(args):
    return runner.invoke(app, args)


def test_phase3_hybrid_lifecycle(fake_embeddings, tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    assert _run(["init", str(proj), "--target", "generic", "--yes"]).exit_code == 0
    wiki = proj / "wiki"

    _run(["new-page", "Neural Networks", "--type", "concept", "--summary", "deep learning models",
          "--wiki", str(wiki)])
    _run(["new-page", "Bicycle Repair", "--type", "concept", "--summary", "fixing bikes",
          "--wiki", str(wiki)])

    # build the vector index
    r = _run(["embed", "--wiki", str(wiki)])
    assert r.exit_code == 0
    assert "2 added" in r.stdout

    # hybrid search (backend + index present) finds the relevant page
    r = _run(["search", "neural networks", "--wiki", str(wiki)])
    assert r.exit_code == 0
    assert "neural-networks" in r.stdout

    # similar works
    assert _run(["similar", "neural-networks", "--json", "--wiki", str(wiki)]).exit_code == 0

    # editing one page re-embeds only it
    p = wiki / "pages" / "neural-networks.md"
    fm, body = parse(p.read_text())
    p.write_text(dump(fm, body + "\nmore transformers attention\n"))
    r = _run(["embed", "--wiki", str(wiki)])
    assert r.exit_code == 0
    assert "1 updated" in r.stdout

    # doctor reports the index present
    r = _run(["doctor", "--wiki", str(wiki)])
    assert r.exit_code == 0
    assert "vectors indexed" in r.stdout
