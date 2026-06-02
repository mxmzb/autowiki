from __future__ import annotations

from .config import WikiConfig
from .frontmatter import today


def append_log(cfg: WikiConfig, action: str, title: str, note: str | None = None) -> None:
    """Append a canonical `## [YYYY-MM-DD] <action> | <title>` entry to log.md."""
    entry = f"## [{today()}] {action} | {title}\n"
    if note:
        entry += f"> {note}\n"

    path = cfg.log_file
    if not path.exists():
        path.write_text("# Log\n\n" + entry, encoding="utf-8")
        return

    existing = path.read_text(encoding="utf-8")
    if not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + "\n" + entry, encoding="utf-8")
