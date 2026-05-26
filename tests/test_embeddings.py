import math

from llm_wiki import embeddings
from llm_wiki.config import WikiConfig


def _cos(x, y):
    dot = sum(a * b for a, b in zip(x, y))
    nx = math.sqrt(sum(a * a for a in x))
    ny = math.sqrt(sum(b * b for b in y))
    return dot / (nx * ny) if nx and ny else 0.0


def test_import_does_not_require_fastembed():
    # Importing the module must never require the optional deps.
    assert hasattr(embeddings, "get_backend")
    assert hasattr(embeddings, "available")


def test_get_backend_returns_override(fake_embeddings, wiki_cfg: WikiConfig):
    backend = embeddings.get_backend(wiki_cfg)
    assert backend is not None
    assert backend.name == "fake"
    assert embeddings.available(wiki_cfg) is True


def test_no_backend_when_not_overridden_and_lib_absent(wiki_cfg: WikiConfig):
    # With no override and fastembed not installed in the dev env, local is unavailable.
    assert embeddings.get_backend(wiki_cfg) is None
    assert embeddings.available(wiki_cfg) is False


def test_fake_backend_deterministic_and_reflects_overlap(fake_embeddings, wiki_cfg: WikiConfig):
    backend = embeddings.get_backend(wiki_cfg)
    v1 = backend.embed(["neural networks deep learning"])[0]
    v1_again = backend.embed(["neural networks deep learning"])[0]
    assert v1 == v1_again  # deterministic

    base, close, far = backend.embed(["neural networks", "neural networks models", "bicycle repair"])
    assert _cos(base, close) > _cos(base, far)
