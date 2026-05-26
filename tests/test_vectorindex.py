from llm_wiki import embeddings
from llm_wiki.config import WikiConfig
from llm_wiki.frontmatter import dump, parse
from llm_wiki.pages import new_page
from llm_wiki.vectorindex import build_or_update, load, query_vector, similar


def test_build_writes_store(fake_embeddings, wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Neural Networks", summary="deep learning models")
    new_page(wiki_cfg, type="concept", title="Bicycles", summary="pedal vehicles")
    backend = embeddings.get_backend(wiki_cfg)
    summary = build_or_update(wiki_cfg, backend)
    assert summary["added"] == 2
    loaded = load(wiki_cfg)
    assert loaded is not None
    slugs, matrix = loaded
    assert set(slugs) == {"neural-networks", "bicycles"}
    assert matrix.shape[0] == 2


def test_incremental_unchanged_then_updated(fake_embeddings, wiki_cfg: WikiConfig):
    p = new_page(wiki_cfg, type="concept", title="A", summary="alpha beta")
    backend = embeddings.get_backend(wiki_cfg)
    build_or_update(wiki_cfg, backend)
    again = build_or_update(wiki_cfg, backend)
    assert again == {"added": 0, "updated": 0, "removed": 0, "unchanged": 1}

    fm, body = parse(p.read_text())
    p.write_text(dump(fm, body + "\nmore text gamma\n"))
    after_edit = build_or_update(wiki_cfg, backend)
    assert after_edit["updated"] == 1


def test_removed_page_drops_from_store(fake_embeddings, wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Keep", summary="x")
    p = new_page(wiki_cfg, type="concept", title="Drop", summary="y")
    backend = embeddings.get_backend(wiki_cfg)
    build_or_update(wiki_cfg, backend)
    p.unlink()
    summary = build_or_update(wiki_cfg, backend)
    assert summary["removed"] == 1
    slugs, _ = load(wiki_cfg)
    assert "drop" not in slugs


def test_similar_ranks_overlap_first(fake_embeddings, wiki_cfg: WikiConfig):
    new_page(wiki_cfg, type="concept", title="Neural Networks", summary="deep learning neural")
    new_page(wiki_cfg, type="concept", title="Deep Learning", summary="neural deep models")
    new_page(wiki_cfg, type="concept", title="Bicycle", summary="pedal wheels")
    build_or_update(wiki_cfg, embeddings.get_backend(wiki_cfg))
    res = similar(wiki_cfg, "neural-networks", limit=2)
    assert res[0][0] == "deep-learning"


def test_query_vector_empty_without_store(fake_embeddings, wiki_cfg: WikiConfig):
    backend = embeddings.get_backend(wiki_cfg)
    assert query_vector(wiki_cfg, [0.0] * backend.dim) == []


def test_load_returns_none_on_torn_write(fake_embeddings, wiki_cfg: WikiConfig):
    import json

    import numpy as np

    new_page(wiki_cfg, type="concept", title="A", summary="x")
    build_or_update(wiki_cfg, embeddings.get_backend(wiki_cfg))
    # simulate a torn write: matrix rows no longer match the stored slug count
    meta = json.loads((wiki_cfg.index_dir / "embeddings.json").read_text())
    np.save(wiki_cfg.index_dir / "vectors.npy", np.zeros((5, meta["dim"]), dtype="float32"))
    assert load(wiki_cfg) is None  # inconsistent store treated as absent (rebuilds next embed)
