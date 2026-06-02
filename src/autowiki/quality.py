from __future__ import annotations

from collections.abc import Callable

from .config import WikiConfig
from .frontmatter import PageFrontmatter
from .pages import list_page_paths, load_page

# Deterministic quality signals (weights sum to 1.0). Report-only — does not gate
# search or the index.
_CHECKS: list[tuple[Callable[[PageFrontmatter, str], bool], float, str]] = [
    (lambda fm, body: bool(fm.summary.strip()), 0.20, "summary"),
    (lambda fm, body: bool(fm.sources), 0.15, "sources"),
    (lambda fm, body: len(body.split()) >= 30, 0.20, "body"),
    (lambda fm, body: fm.confidence is not None, 0.15, "confidence"),
    (lambda fm, body: ("[[" in body) or bool(fm.related), 0.15, "links"),
    (lambda fm, body: bool(fm.tags), 0.15, "tags"),
]


def quality_score(fm: PageFrontmatter, body: str) -> tuple[float, list[str]]:
    score = 0.0
    missing: list[str] = []
    for check, weight, name in _CHECKS:
        if check(fm, body):
            score += weight
        else:
            missing.append(name)
    return round(min(1.0, score), 2), missing


def quality_report(cfg: WikiConfig, limit: int | None = None) -> list[dict]:
    out: list[dict] = []
    for path in list_page_paths(cfg):
        try:
            fm, body = load_page(path)
        except Exception:
            continue
        slug = fm.slug or path.stem
        score, missing = quality_score(fm, body)
        out.append({"slug": slug, "score": score, "missing": missing})
    out.sort(key=lambda d: (d["score"], d["slug"]))
    return out[:limit] if limit else out
