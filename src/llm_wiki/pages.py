from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from .assets import load_template, page_template_name
from .config import WikiConfig
from .frontmatter import PageFrontmatter, dump, parse, today, validate

_SLUG_RE = re.compile(r"[^a-z0-9]+")

_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`]*`")


def slugify(text: str) -> str:
    """Turn a title into a kebab-case slug."""
    return _SLUG_RE.sub("-", text.lower()).strip("-")


def extract_links(body: str) -> list[str]:
    """Wiki-link targets (`[[slug]]`) in `body`, ignoring code fences and inline
    code spans — so e.g. a Next.js `[[...slug]]` route path is never a link."""
    without_code = _FENCED_CODE_RE.sub(" ", body)
    without_code = _INLINE_CODE_RE.sub(" ", without_code)
    return _LINK_RE.findall(without_code)


def list_page_paths(cfg: WikiConfig) -> list[Path]:
    """All markdown page files, sorted by path."""
    if not cfg.pages_dir.exists():
        return []
    return sorted(p for p in cfg.pages_dir.glob("*.md") if p.is_file())


def load_page(path: Path) -> tuple[PageFrontmatter, str]:
    return parse(path.read_text(encoding="utf-8"))


def _body_for(page_type: str) -> str:
    """Per-type body template, or empty for custom types without one."""
    try:
        return load_template(page_template_name(page_type))
    except (FileNotFoundError, ModuleNotFoundError):
        return ""


def new_page(
    cfg: WikiConfig,
    type: str,
    title: str,
    summary: str = "",
    tags: Iterable[str] = (),
    sources: Iterable[str] = (),
    slug: str | None = None,
    tier: str = "semantic",
    confidence: float | None = None,
    evergreen: bool = False,
) -> Path:
    """Create a page file with correct frontmatter and a per-type body template."""
    if type not in cfg.allowed_types:
        raise ValueError(
            f"unknown page type: {type!r} (allowed: {', '.join(cfg.allowed_types)})"
        )
    slug = slug or slugify(title)
    if not slug:
        raise ValueError(f"could not derive a slug from title {title!r}; pass an explicit slug")
    path = cfg.pages_dir / f"{slug}.md"
    if path.exists():
        raise FileExistsError(f"page already exists: {path.name} (try slug {slug}-2)")

    cfg.pages_dir.mkdir(parents=True, exist_ok=True)
    now = today()
    fm = PageFrontmatter(
        title=title,
        type=type,
        created=now,
        updated=now,
        slug=slug,
        summary=summary,
        tags=list(tags),
        sources=list(sources),
        tier=tier,
        confidence=confidence,
        evergreen=evergreen,
    )
    path.write_text(dump(fm, _body_for(type)), encoding="utf-8")
    return path


_UNSET = object()


def set_page_fields(
    cfg: WikiConfig,
    slug: str,
    *,
    confidence: float | None = _UNSET,  # type: ignore[assignment]
    tier: str = _UNSET,  # type: ignore[assignment]
    status: str = _UNSET,  # type: ignore[assignment]
    review_by: str | None = _UNSET,  # type: ignore[assignment]
    evergreen: bool = _UNSET,  # type: ignore[assignment]
    add_sources: Iterable[str] = (),
    add_related: Iterable[str] = (),
    add_tags: Iterable[str] = (),
) -> Path:
    """Update lifecycle fields on an existing page's frontmatter and bump `updated`.

    Only fields explicitly passed are changed; list fields are appended (deduped).
    Validates the result and raises ValueError without writing if it would be invalid.
    """
    path = cfg.pages_dir / f"{slug}.md"
    if not path.exists():
        raise FileNotFoundError(slug)
    fm, body = load_page(path)

    if confidence is not _UNSET:
        fm.confidence = confidence
    if tier is not _UNSET:
        fm.tier = tier
    if status is not _UNSET:
        fm.status = status
    if review_by is not _UNSET:
        fm.review_by = review_by
    if evergreen is not _UNSET:
        fm.evergreen = bool(evergreen)
    for value, target in ((add_sources, fm.sources), (add_related, fm.related), (add_tags, fm.tags)):
        for item in value:
            if item not in target:
                target.append(item)

    errors = validate(fm, cfg.allowed_types)
    if errors:
        raise ValueError("; ".join(errors))
    fm.updated = today()
    path.write_text(dump(fm, body), encoding="utf-8")
    return path
