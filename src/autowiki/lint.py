from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass

from .catalog import index_is_current, write_index
from .config import WikiConfig
from .frontmatter import PageFrontmatter, dump, today, validate
from .pages import extract_links, list_page_paths, load_page


@dataclass
class LintIssue:
    level: str  # "error" | "warning" | "info"
    code: str
    page: str  # slug, or "" for wiki-level issues
    message: str


def _days_old(date_str: str) -> int:
    try:
        d = dt.date.fromisoformat(str(date_str))
    except (ValueError, TypeError):
        return 0
    return (dt.date.today() - d).days


def run_lint(cfg: WikiConfig) -> list[LintIssue]:
    """Structural health check. Tolerant: never crashes on a malformed page."""
    issues: list[LintIssue] = []

    # Parse pass — unparseable pages become bad_frontmatter issues, not crashes.
    parsed: list[tuple[str, PageFrontmatter, str]] = []  # (slug, fm, body)
    for path in list_page_paths(cfg):
        try:
            fm, body = load_page(path)
        except Exception as exc:  # noqa: BLE001 — any parse failure is reported, not raised
            issues.append(
                LintIssue("error", "bad_frontmatter", path.stem, f"could not parse: {exc}")
            )
            continue
        parsed.append((fm.slug or path.stem, fm, body))

    # Invalid frontmatter (required fields / enums).
    for slug, fm, _body in parsed:
        for msg in validate(fm, cfg.allowed_types):
            issues.append(LintIssue("error", "invalid_frontmatter", slug, msg))

    # Known link targets: slugs + aliases.
    known: set[str] = set()
    for slug, fm, _body in parsed:
        known.add(slug)
        known.update(fm.aliases)

    # Duplicate slugs.
    for slug, count in Counter(slug for slug, _fm, _b in parsed).items():
        if count > 1:
            issues.append(
                LintIssue("error", "duplicate_slug", slug, f"{count} pages share slug {slug!r}")
            )

    # Links (wiki-links in body + relational frontmatter) → broken + inbound set.
    inbound: set[str] = set()
    for slug, fm, body in parsed:
        targets = set(extract_links(body))
        targets |= set(fm.related) | set(fm.supersedes) | set(fm.superseded_by) | set(fm.contradicts)
        targets |= {str(rel["target"]) for rel in fm.relations if isinstance(rel, dict) and rel.get("target")}
        for raw in targets:
            target = raw.strip()
            if not target:
                continue
            inbound.add(target)
            if target not in known:
                issues.append(LintIssue("error", "broken_link", slug, f"unresolved link: {target}"))

    # Orphans (no inbound links via wiki-links or relational frontmatter).
    for slug, fm, _body in parsed:
        if slug not in inbound and not any(a in inbound for a in fm.aliases):
            issues.append(LintIssue("warning", "orphan", slug, "no inbound links"))

    # Missing sources.
    inbox_ids: set[str] = set()
    if cfg.inbox_dir.exists():
        inbox_ids = {p.stem for p in cfg.inbox_dir.iterdir() if p.is_file() and p.name != ".gitkeep"}
    for slug, fm, _body in parsed:
        for sid in fm.sources:
            if sid not in inbox_ids:
                issues.append(LintIssue("error", "missing_source", slug, f"source not in inbox: {sid}"))

    # Supersession consistency + archived-status (lifecycle).
    fm_by_slug = {slug: fm for slug, fm, _ in parsed}
    for slug, fm, _body in parsed:
        for target in fm.supersedes:
            t = str(target).strip()
            if t in fm_by_slug and slug not in fm_by_slug[t].superseded_by:
                issues.append(
                    LintIssue("error", "supersession_inconsistent", slug, f"supersedes {t}, but {t} lacks superseded_by: {slug}")
                )
        for target in fm.superseded_by:
            t = str(target).strip()
            if t in fm_by_slug and slug not in fm_by_slug[t].supersedes:
                issues.append(
                    LintIssue("error", "supersession_inconsistent", slug, f"superseded_by {t}, but {t} lacks supersedes: {slug}")
                )
        if fm.superseded_by and fm.status != "superseded":
            issues.append(
                LintIssue("warning", "archived_status", slug, "has superseded_by but status is not 'superseded'")
            )

    # Stale (review_by passed, or not updated within stale_days). Evergreen pages never go stale.
    today_s = today()
    for slug, fm, _body in parsed:
        if fm.evergreen:
            continue
        if fm.review_by and str(fm.review_by) < today_s:
            issues.append(LintIssue("warning", "stale", slug, f"review_by {fm.review_by} has passed"))
        elif fm.updated and _days_old(fm.updated) > cfg.stale_days:
            issues.append(
                LintIssue("warning", "stale", slug, f"not updated in over {cfg.stale_days} days")
            )

    # Index freshness.
    if not index_is_current(cfg):
        issues.append(
            LintIssue("warning", "index_stale", "", "index.md is out of date; run `autowiki index`")
        )

    # Structural contradiction hook (semantic resolution is Phase 5).
    for slug, fm, _body in parsed:
        for target in fm.contradicts:
            issues.append(
                LintIssue("info", "contradiction", slug, f"declares contradiction with {target}")
            )

    return issues


def fix(cfg: WikiConfig) -> list[LintIssue]:
    """Apply safe auto-repairs (normalize frontmatter, rebuild index), return what remains."""
    for path in list_page_paths(cfg):
        try:
            fm, body = load_page(path)
        except Exception:  # noqa: BLE001 — can't safely normalize an unparseable page
            continue
        path.write_text(dump(fm, body), encoding="utf-8")
    write_index(cfg)
    return run_lint(cfg)
