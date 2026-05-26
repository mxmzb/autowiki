from __future__ import annotations

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

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


def search(
    cfg: WikiConfig,
    query: str,
    type: str | None = None,
    tag: str | None = None,
    limit: int = 10,
) -> list[Hit]:
    """BM25 ranking over pages (title+summary+tags+body), filtered by type/tag.

    Single retriever entry point; Phase 3 adds a vector leg + rank fusion here.
    """
    q = _tokenize(query)
    if not q:
        return []

    docs: list[tuple[str, str, str, list[str]]] = []  # slug, title, snippet, tokens
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
        docs.append((slug, fm.title or slug, _snippet(body), _tokenize(text)))

    if not docs:
        return []

    bm25 = BM25Okapi([d[3] for d in docs])
    scores = bm25.get_scores(q)
    qset = set(q)
    # A page is a hit if it contains at least one query term, ranked by BM25 score.
    # (Don't filter on score > 0: with a tiny corpus BM25's IDF floors to 0 for a
    # term present in ~half the docs, which would drop genuine matches.)
    hits = [
        Hit(slug=d[0], title=d[1], score=float(s), snippet=d[2])
        for d, s in zip(docs, scores)
        if qset & set(d[3])
    ]
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]
