from __future__ import annotations

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from . import embeddings, vectorindex
from .config import WikiConfig
from .pages import list_page_paths, load_page

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class Hit:
    slug: str
    title: str
    score: float
    snippet: str


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _snippet(body: str, n: int = 160) -> str:
    return " ".join(body.split())[:n]


def _documents(cfg: WikiConfig, type: str | None, tag: str | None) -> list[dict]:
    docs: list[dict] = []
    for path in list_page_paths(cfg):
        try:
            fm, body = load_page(path)
        except Exception:
            continue
        if type and fm.type != type:
            continue
        if tag and tag not in fm.tags:
            continue
        slug = fm.slug or path.stem
        text = " ".join([fm.title, fm.summary, " ".join(fm.tags), body])
        docs.append(
            {"slug": slug, "title": fm.title or slug, "snippet": _snippet(body), "tokens": _tokenize(text)}
        )
    return docs


def _bm25_ranked(docs: list[dict], query_tokens: list[str]) -> list[tuple[str, float]]:
    if not docs:
        return []
    bm25 = BM25Okapi([d["tokens"] for d in docs])
    scores = bm25.get_scores(query_tokens)
    qset = set(query_tokens)
    # A page is a hit if it contains at least one query term (BM25's tiny-corpus IDF
    # can floor to 0, so don't filter on score > 0).
    scored = [(d["slug"], float(s)) for d, s in zip(docs, scores) if qset & set(d["tokens"])]
    scored.sort(key=lambda kv: kv[1], reverse=True)
    return scored


def _rrf(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """Reciprocal rank fusion of ranked slug lists."""
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, slug in enumerate(ranking):
            fused[slug] = fused.get(slug, 0.0) + 1.0 / (k + rank + 1)
    return fused


def _hit(doc: dict, score: float) -> Hit:
    return Hit(slug=doc["slug"], title=doc["title"], score=float(score), snippet=doc["snippet"])


def search(
    cfg: WikiConfig,
    query: str,
    type: str | None = None,
    tag: str | None = None,
    limit: int = 10,
    hybrid: bool | None = None,
) -> list[Hit]:
    """BM25 search, fused with vector retrieval (RRF) when an embedding backend and
    a vector index are available. `hybrid=False` forces BM25-only."""
    tokens = _tokenize(query)
    if not tokens:
        return []
    docs = _documents(cfg, type, tag)
    if not docs:
        return []
    by_slug = {d["slug"]: d for d in docs}
    bm25 = _bm25_ranked(docs, tokens)

    vector_slugs: list[str] = []
    if hybrid is not False and embeddings.available(cfg):
        backend = embeddings.get_backend(cfg)
        if backend is not None and vectorindex.load(cfg) is not None:
            qvec = backend.embed([query])[0]
            vector_slugs = [
                slug
                for slug, _score in vectorindex.query_vector(cfg, qvec, limit=max(limit * 3, 10))
                if slug in by_slug
            ]

    if not vector_slugs:
        return [_hit(by_slug[slug], score) for slug, score in bm25[:limit]]

    fused = _rrf([[slug for slug, _ in bm25], vector_slugs])
    ordered = sorted(fused, key=lambda slug: (-fused[slug], slug))
    return [_hit(by_slug[slug], fused[slug]) for slug in ordered if slug in by_slug][:limit]
