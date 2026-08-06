import json
from pathlib import Path

from typer.testing import CliRunner

from autowiki.cli import app
from autowiki.frontmatter import dump, parse

runner = CliRunner()


def _run(args):
    return runner.invoke(app, args)


def test_phase4_lifecycle(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    assert _run(["init", str(proj), "--target", "generic", "--yes"]).exit_code == 0
    wiki = proj / "wiki"

    _run(["new-page", "Timeless Definition", "--type", "concept", "--evergreen",
          "--summary", "always true", "--wiki", str(wiki)])
    _run(["new-page", "Stale Thing", "--type", "note", "--tier", "working",
          "--summary", "old note", "--wiki", str(wiki)])
    _run(["new-page", "Old Way", "--type", "concept", "--summary", "deprecated approach", "--wiki", str(wiki)])
    _run(["new-page", "New Way", "--type", "concept", "--summary", "current approach", "--wiki", str(wiki)])

    # backdate the stale page so it's overdue
    page = wiki / "pages" / "stale-thing.md"
    fm, body = parse(page.read_text())
    fm.review_by = "2000-01-01"
    page.write_text(dump(fm, body))

    # review surfaces the stale page, omits the evergreen one
    r = _run(["review", "--json", "--wiki", str(wiki)])
    assert r.exit_code == 0
    slugs = {x["slug"] for x in json.loads(r.stdout)}
    assert "stale-thing" in slugs
    assert "timeless-definition" not in slugs

    # supersede: old leaves the index but stays searchable
    assert _run(["supersede", "old-way", "new-way", "--wiki", str(wiki)]).exit_code == 0
    _run(["index", "--wiki", str(wiki)])
    assert "[[old-way]]" not in (wiki / "index.md").read_text()
    assert "old-way" in _run(["search", "deprecated approach", "--wiki", str(wiki)]).stdout

    # supersede left the relationship consistent (no supersession errors)
    lint_json = _run(["lint", "--json", "--wiki", str(wiki)])
    codes = {i["code"] for i in json.loads(lint_json.stdout)}
    assert "supersession_inconsistent" not in codes

    # status reflects the lifecycle
    rstat = _run(["status", "--wiki", str(wiki)])
    assert rstat.exit_code == 0
    assert "Review due:" in rstat.stdout
