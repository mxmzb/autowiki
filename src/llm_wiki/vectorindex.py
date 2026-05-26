from __future__ import annotations

import hashlib
import json

from .config import WikiConfig
from .embeddings import EmbeddingBackend
from .frontmatter import PageFrontmatter
from .pages import list_page_paths, load_page


def page_text(fm: PageFrontmatter, body: str) -> str:
    return " ".join([fm.title, fm.summary, " ".join(fm.tags), body])


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _meta_path(cfg: WikiConfig):
    return cfg.index_dir / "embeddings.json"


def _vectors_path(cfg: WikiConfig):
    return cfg.index_dir / "vectors.npy"


def _current_pages(cfg: WikiConfig) -> dict[str, tuple[str, str]]:
    """slug -> (content_hash, text) for every parseable page."""
    out: dict[str, tuple[str, str]] = {}
    for path in list_page_paths(cfg):
        try:
            fm, body = load_page(path)
        except Exception:
            continue
        slug = fm.slug or path.stem
        text = page_text(fm, body)
        out[slug] = (content_hash(text), text)
    return out


def load(cfg: WikiConfig):
    """Return (slugs, matrix) or None if no store exists."""
    import numpy as np

    if not (_meta_path(cfg).exists() and _vectors_path(cfg).exists()):
        return None
    meta = json.loads(_meta_path(cfg).read_text(encoding="utf-8"))
    return meta["slugs"], np.load(_vectors_path(cfg))


def build_or_update(cfg: WikiConfig, backend: EmbeddingBackend) -> dict:
    """Embed new/changed pages incrementally; drop removed ones. Returns counts."""
    import numpy as np

    cfg.index_dir.mkdir(parents=True, exist_ok=True)
    current = _current_pages(cfg)

    meta_path = _meta_path(cfg)
    existing = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    same_model = existing.get("model") == backend.name
    old_hashes: dict = existing.get("hashes", {}) if same_model else {}

    old_vectors: dict = {}
    if same_model and _vectors_path(cfg).exists():
        matrix = np.load(_vectors_path(cfg))
        for i, slug in enumerate(existing.get("slugs", [])):
            old_vectors[slug] = matrix[i]

    added = updated = unchanged = 0
    vectors: dict = {}
    to_embed: list[tuple[str, str]] = []
    for slug, (h, text) in current.items():
        if slug in old_vectors and old_hashes.get(slug) == h:
            vectors[slug] = old_vectors[slug]
            unchanged += 1
        else:
            to_embed.append((slug, text))
            if slug in old_hashes:
                updated += 1
            else:
                added += 1

    if to_embed:
        embedded = backend.embed([text for _slug, text in to_embed])
        for (slug, _text), vec in zip(to_embed, embedded):
            vectors[slug] = np.asarray(vec, dtype="float32")

    removed = sum(1 for slug in old_hashes if slug not in current)

    slugs = sorted(vectors)
    if slugs:
        out_matrix = np.vstack([vectors[s] for s in slugs]).astype("float32")
    else:
        out_matrix = np.zeros((0, int(backend.dim)), dtype="float32")
    np.save(_vectors_path(cfg), out_matrix)
    meta_path.write_text(
        json.dumps(
            {
                "model": backend.name,
                "dim": int(backend.dim),
                "slugs": slugs,
                "hashes": {s: current[s][0] for s in slugs},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"added": added, "updated": updated, "removed": removed, "unchanged": unchanged}


def query_vector(cfg: WikiConfig, vector, limit: int = 10) -> list[tuple[str, float]]:
    import numpy as np

    loaded = load(cfg)
    if loaded is None:
        return []
    slugs, matrix = loaded
    if matrix.shape[0] == 0:
        return []
    q = np.asarray(vector, dtype="float32")
    qn = float(np.linalg.norm(q))
    if qn == 0.0:
        return []
    sims = (matrix @ q) / (np.linalg.norm(matrix, axis=1) * qn + 1e-12)
    order = np.argsort(-sims)[:limit]
    return [(slugs[i], float(sims[i])) for i in order]


def similar(cfg: WikiConfig, slug: str, limit: int = 10) -> list[tuple[str, float]]:
    """Nearest pages to `slug` by stored vector (excludes self). Raises KeyError if not indexed."""
    loaded = load(cfg)
    if loaded is None:
        return []
    slugs, matrix = loaded
    if slug not in slugs:
        raise KeyError(slug)
    vector = matrix[slugs.index(slug)]
    return [(s, score) for s, score in query_vector(cfg, vector, limit=limit + 1) if s != slug][:limit]
