from pathlib import Path

from typer.testing import CliRunner

from autowiki.cli import app

runner = CliRunner()


def test_full_ingest_loop(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    assert runner.invoke(app, ["init", str(proj), "--target", "generic"]).exit_code == 0
    wiki = proj / "wiki"

    # A raw source file to ingest.
    src = tmp_path / "article.txt"
    src.write_text("Karpathy on neural networks and large language models.")

    # add-source → prints the id.
    r = runner.invoke(app, ["add-source", str(src), "--wiki", str(wiki)])
    assert r.exit_code == 0, r.stdout
    sid = r.stdout.strip()
    assert sid == "article"
    assert list(wiki.glob("inbox/article.*"))

    # new-page referencing that source.
    r = runner.invoke(
        app,
        [
            "new-page",
            "Neural Networks",
            "--type",
            "concept",
            "--summary",
            "intro to neural networks",
            "--sources",
            sid,
            "--wiki",
            str(wiki),
        ],
    )
    assert r.exit_code == 0, r.stdout
    assert (wiki / "pages" / "neural-networks.md").exists()

    # index → log → lint (clean of errors; orphan/other warnings are allowed).
    assert runner.invoke(app, ["index", "--wiki", str(wiki)]).exit_code == 0
    assert runner.invoke(app, ["log", "ingest", "Neural Networks", "--wiki", str(wiki)]).exit_code == 0
    r = runner.invoke(app, ["lint", "--wiki", str(wiki)])
    assert r.exit_code == 0, r.stdout  # no error-level issues

    # search finds the page.
    r = runner.invoke(app, ["search", "neural networks", "--wiki", str(wiki)])
    assert r.exit_code == 0
    assert "neural-networks" in r.stdout


def test_command_outside_a_wiki_errors(tmp_path: Path):
    r = runner.invoke(app, ["lint", "--wiki", str(tmp_path)])
    assert r.exit_code == 1
    assert "No wiki found" in (r.stdout + str(r.stderr))


def test_index_check_flags_stale(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    runner.invoke(app, ["init", str(proj), "--target", "generic"])
    wiki = proj / "wiki"
    runner.invoke(
        app, ["new-page", "Solo", "--type", "note", "--wiki", str(wiki)]
    )
    # A page was added but index not rebuilt → --check should exit 2.
    assert runner.invoke(app, ["index", "--check", "--wiki", str(wiki)]).exit_code == 2
    runner.invoke(app, ["index", "--wiki", str(wiki)])
    assert runner.invoke(app, ["index", "--check", "--wiki", str(wiki)]).exit_code == 0
