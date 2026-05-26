import hashlib
import re
from pathlib import Path

import pytest

from llm_wiki import embeddings
from llm_wiki.config import WikiConfig
from llm_wiki.scaffold import init_wiki


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A clean temporary project directory."""
    return tmp_path


@pytest.fixture
def wiki_cfg(project: Path) -> WikiConfig:
    """An initialized wiki (generic target) returning its WikiConfig."""
    cfg, _ = init_wiki(project, target="generic")
    return cfg


class FakeBackend:
    """Deterministic, dependency-free embedding for tests: feature-hashed bag of
    words, so more shared words ⇒ higher cosine. No model downloads."""

    name = "fake"
    dim = 64

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in re.findall(r"[a-z0-9]+", text.lower()):
                idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dim
                vec[idx] += 1.0
            out.append(vec)
        return out


@pytest.fixture
def fake_embeddings():
    """Activate the FakeBackend for the duration of a test."""
    embeddings.set_test_backend(FakeBackend())
    yield
    embeddings.clear_test_backend()
