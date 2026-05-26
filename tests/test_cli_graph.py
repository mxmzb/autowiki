import json

from typer.testing import CliRunner

from llm_wiki.cli import app
from llm_wiki.config import WikiConfig
from llm_wiki.frontmatter import dump, parse
from llm_wiki.pages import new_page

runner = CliRunner()


def _setup(wiki_cfg: WikiConfig) -> None:
    new_page(wiki_cfg, type="entity", title="A")
    new_page(wiki_cfg, type="concept", title="B")
    p = wiki_cfg.pages_dir / "a.md"
    fm, body = parse(p.read_text())
    p.write_text(dump(fm, body + "\n[[b]]\n"))


def test_graph_neighbors(wiki_cfg: WikiConfig):
    _setup(wiki_cfg)
    r = runner.invoke(app, ["graph", "neighbors", "a", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert "b" in r.stdout


def test_graph_path(wiki_cfg: WikiConfig):
    _setup(wiki_cfg)
    r = runner.invoke(app, ["graph", "path", "a", "b", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert "a -> b" in r.stdout


def test_graph_hubs_json(wiki_cfg: WikiConfig):
    _setup(wiki_cfg)
    r = runner.invoke(app, ["graph", "hubs", "--json", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert any(h["slug"] == "b" for h in json.loads(r.stdout))


def test_graph_stats(wiki_cfg: WikiConfig):
    _setup(wiki_cfg)
    r = runner.invoke(app, ["graph", "stats", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert "Nodes: 2" in r.stdout


def test_graph_export_dot(wiki_cfg: WikiConfig):
    _setup(wiki_cfg)
    r = runner.invoke(app, ["graph", "export", "--format", "dot", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert r.stdout.strip().startswith("digraph")


def test_graph_neighbors_missing_slug_exits_1(wiki_cfg: WikiConfig):
    _setup(wiki_cfg)
    r = runner.invoke(app, ["graph", "neighbors", "nope", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 1
