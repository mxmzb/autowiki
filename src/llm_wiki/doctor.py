from __future__ import annotations

from . import embeddings, lifecycle, vectorindex
from .config import SCHEMA_VERSION, WikiConfig
from .hooks import hooks_installed
from .lint import run_lint
from .managed_block import BEGIN
from .pages import list_page_paths, load_page
from .scaffold import project_root_of


def doctor(cfg: WikiConfig) -> list[tuple[str, str]]:
    """Health/setup check. Returns (level, message) where level is ok|warn|error."""
    out: list[tuple[str, str]] = []

    if cfg.schema_version < SCHEMA_VERSION:
        out.append(
            ("warn", f"wiki schema v{cfg.schema_version} < tool v{SCHEMA_VERSION}; run `llm-wiki upgrade`")
        )
    elif cfg.schema_version > SCHEMA_VERSION:
        out.append(
            ("error", f"wiki schema v{cfg.schema_version} > tool v{SCHEMA_VERSION}; upgrade the llm-wiki tool")
        )
    else:
        out.append(("ok", f"schema v{cfg.schema_version}"))

    for label, path in (
        ("pages/", cfg.pages_dir),
        ("inbox/", cfg.inbox_dir),
        ("SCHEMA.md", cfg.schema_file),
        ("index.md", cfg.index_file),
        ("log.md", cfg.log_file),
    ):
        out.append(("ok", f"{label} present") if path.exists() else ("error", f"missing {label}"))

    project_root, _ = project_root_of(cfg)
    block_file = project_root / ("CLAUDE.md" if cfg.target == "claude" else "AGENTS.md")
    if block_file.exists() and BEGIN in block_file.read_text(encoding="utf-8"):
        out.append(("ok", f"managed block present in {block_file.name}"))
    else:
        out.append(("warn", f"managed block missing from {block_file.name}; run `llm-wiki upgrade`"))

    out.append(("ok", f"hooks {'installed' if hooks_installed(project_root) else 'not installed'}"))

    if not embeddings.available(cfg):
        out.append(("ok", "embeddings: not installed (keyword search only) — `pip install llm-wiki[embeddings]`"))
    else:
        loaded = vectorindex.load(cfg)
        if loaded is None:
            out.append(("warn", f"embeddings available ({cfg.embedding_provider}); no index — run `llm-wiki embed`"))
        else:
            # Compare against the parseable (embeddable) set, not raw file count,
            # so an unparseable page doesn't read as a permanent "stale" index.
            indexed, page_count = len(loaded[0]), len(vectorindex._current_pages(cfg))
            if indexed != page_count:
                out.append(("warn", f"vector index stale ({indexed} indexed vs {page_count} pages); run `llm-wiki embed`"))
            else:
                out.append(("ok", f"embeddings available; {indexed} vectors indexed"))
    return out


def status(cfg: WikiConfig) -> dict:
    """Content overview: counts by type/status/tier, last log entry, lint + review counts."""
    counts: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_tier: dict[str, int] = {}
    for path in list_page_paths(cfg):
        try:
            fm, _ = load_page(path)
        except Exception:
            counts["(unparseable)"] = counts.get("(unparseable)", 0) + 1
            continue
        counts[fm.type or "untyped"] = counts.get(fm.type or "untyped", 0) + 1
        by_status[fm.status] = by_status.get(fm.status, 0) + 1
        by_tier[fm.tier] = by_tier.get(fm.tier, 0) + 1

    last_log = ""
    if cfg.log_file.exists():
        for line in reversed(cfg.log_file.read_text(encoding="utf-8").splitlines()):
            if line.startswith("## ["):
                last_log = line.lstrip("# ").strip()
                break

    issues = run_lint(cfg)
    return {
        "counts": counts,
        "total": sum(counts.values()),
        "by_status": by_status,
        "by_tier": by_tier,
        "review_due": len(lifecycle.review(cfg)),
        "last_log": last_log,
        "lint_errors": sum(1 for i in issues if i.level == "error"),
        "lint_warnings": sum(1 for i in issues if i.level == "warning"),
    }
