from __future__ import annotations

import importlib.util
from typing import Protocol

from .config import WikiConfig


class EmbeddingBackend(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


_OVERRIDE: EmbeddingBackend | None = None


def set_test_backend(backend: EmbeddingBackend) -> None:
    """Inject a backend (tests use a deterministic fake — no model downloads)."""
    global _OVERRIDE
    _OVERRIDE = backend


def clear_test_backend() -> None:
    global _OVERRIDE
    _OVERRIDE = None


def available(cfg: WikiConfig) -> bool:
    """Cheap check: can we build a backend? (Does not load any model.)"""
    if _OVERRIDE is not None:
        return True
    if cfg.embedding_provider == "local":
        return importlib.util.find_spec("fastembed") is not None
    return False  # API backends not implemented in Phase 3


def get_backend(cfg: WikiConfig) -> EmbeddingBackend | None:
    """Return a ready backend, or None if unavailable. May load a model (local)."""
    if _OVERRIDE is not None:
        return _OVERRIDE
    if cfg.embedding_provider == "local":
        try:
            return FastEmbedBackend()
        except Exception:
            return None
    return None


class FastEmbedBackend:
    """Local ONNX embeddings via fastembed (no torch). Lazy-imported."""

    DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
    DEFAULT_DIM = 384

    def __init__(self, model: str | None = None) -> None:
        from fastembed import TextEmbedding  # lazy: importing this module never needs fastembed

        self._model_name = model or self.DEFAULT_MODEL
        self._model = TextEmbedding(self._model_name)
        self.name = f"fastembed:{self._model_name}"
        self.dim = self.DEFAULT_DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, vec)) for vec in self._model.embed(list(texts))]
