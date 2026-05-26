from __future__ import annotations

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
    out.append(("ok", f"embedding provider: {cfg.embedding_provider} (vector search lands in Phase 3)"))
    return out


def status(cfg: WikiConfig) -> dict:
    """Content overview: page counts by type, total, last log entry, lint counts."""
    counts: dict[str, int] = {}
    for path in list_page_paths(cfg):
        try:
            fm, _ = load_page(path)
            key = fm.type or "untyped"
        except Exception:
            key = "(unparseable)"
        counts[key] = counts.get(key, 0) + 1

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
        "last_log": last_log,
        "lint_errors": sum(1 for i in issues if i.level == "error"),
        "lint_warnings": sum(1 for i in issues if i.level == "warning"),
    }
