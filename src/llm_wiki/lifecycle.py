from __future__ import annotations

import datetime as dt
import math

from .config import WikiConfig
from .frontmatter import PageFrontmatter, dump, today
from .pages import list_page_paths, load_page

# Per-tier decay strength (larger ⇒ slower decay). Working notes fade fast;
# procedural/semantic knowledge persists.
_TIER_STRENGTH = {"working": 14, "episodic": 60, "semantic": 365, "procedural": 730}
_DEFAULT_STRENGTH = 365


def _age_days(updated: str, now: dt.date) -> int:
    try:
        d = dt.date.fromisoformat(str(updated))
    except (ValueError, TypeError):
        return 0
    return max(0, (now - d).days)


def _confidence(fm: PageFrontmatter) -> float:
    # bool is an int subclass; treat a non-numeric/boolean confidence as "unset".
    if isinstance(fm.confidence, bool) or not isinstance(fm.confidence, (int, float)):
        return 0.5
    return min(1.0, max(0.0, float(fm.confidence)))  # clamp keeps strength > 0 and retention in (0, 1]


def retention(fm: PageFrontmatter, now: dt.date | None = None) -> float:
    """Ebbinghaus-style retention in (0, 1]. Evergreen pages never decay."""
    if fm.evergreen:
        return 1.0
    now = now or dt.date.today()
    age = _age_days(fm.updated, now)
    strength = _TIER_STRENGTH.get(fm.tier, _DEFAULT_STRENGTH) * (0.5 + _confidence(fm))
    return math.exp(-age / strength)


def review(cfg: WikiConfig, threshold: float = 0.5) -> list[dict]:
    """Pages needing attention (overdue / decayed / low-confidence), most-decayed first.
    Evergreen pages are never surfaced."""
    now = dt.date.today()
    out: list[dict] = []
    for path in list_page_paths(cfg):
        try:
            fm, _ = load_page(path)
        except Exception:
            continue
        if fm.evergreen:
            continue
        slug = fm.slug or path.stem
        r = retention(fm, now)
        reasons = []
        if fm.review_by and str(fm.review_by) <= now.isoformat():
            reasons.append("review_by passed")
        if r < threshold:
            reasons.append("decayed")
        if isinstance(fm.confidence, (int, float)) and fm.confidence < 0.3:
            reasons.append("low confidence")
        if reasons:
            out.append({"slug": slug, "title": fm.title or slug, "retention": round(r, 3), "reasons": reasons})
    out.sort(key=lambda d: d["retention"])
    return out


def supersede(cfg: WikiConfig, old_slug: str, new_slug: str) -> None:
    """Mark old_slug as superseded by new_slug, wiring both sides. Idempotent."""
    if old_slug == new_slug:
        raise ValueError("a page cannot supersede itself")
    old_path = cfg.pages_dir / f"{old_slug}.md"
    new_path = cfg.pages_dir / f"{new_slug}.md"
    if not old_path.exists():
        raise FileNotFoundError(old_slug)
    if not new_path.exists():
        raise FileNotFoundError(new_slug)

    old_fm, old_body = load_page(old_path)
    new_fm, new_body = load_page(new_path)

    if new_slug not in old_fm.superseded_by:
        old_fm.superseded_by.append(new_slug)
    old_fm.status = "superseded"
    old_fm.updated = today()
    if old_slug not in new_fm.supersedes:
        new_fm.supersedes.append(old_slug)
    new_fm.updated = today()

    old_path.write_text(dump(old_fm, old_body), encoding="utf-8")
    new_path.write_text(dump(new_fm, new_body), encoding="utf-8")
