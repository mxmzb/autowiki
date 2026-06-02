import json
from pathlib import Path

from typer.testing import CliRunner

from autowiki.cli import app
from autowiki.config import WikiConfig
from autowiki.pages import new_page

runner = CliRunner()


def test_embed_builds_index_and_reports(fake_embeddings, wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Neural Networks", summary="deep learning")
    new_page(wiki_cfg, type="concept", title="Bicycles", summary="pedal vehicles")
    r = runner.invoke(app, ["embed", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    assert "2 added" in r.stdout
    assert (wiki_cfg.index_dir / "vectors.npy").exists()


def test_similar_returns_hits(fake_embeddings, wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Neural Networks", summary="deep learning neural")
    new_page(wiki_cfg, type="concept", title="Deep Learning", summary="neural deep models")
    runner.invoke(app, ["embed", "--wiki", str(wiki_cfg.root)])
    r = runner.invoke(app, ["similar", "neural-networks", "--json", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 0
    data = json.loads(r.stdout)
    assert data and data[0]["slug"] == "deep-learning"


def test_embed_without_backend_exits_1(wiki_cfg: WikiConfig):
    # no fake_embeddings fixture → no backend in the dev env
    r = runner.invoke(app, ["embed", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 1
    assert "autowiki[embeddings]" in (r.stdout + str(r.stderr))


def test_similar_missing_slug_exits_1(fake_embeddings, wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Only", summary="x")
    runner.invoke(app, ["embed", "--wiki", str(wiki_cfg.root)])
    r = runner.invoke(app, ["similar", "ghost", "--wiki", str(wiki_cfg.root)])
    assert r.exit_code == 1
