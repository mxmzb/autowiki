from __future__ import annotations

from .config import WikiConfig
from .frontmatter import PAGE_TYPES
from .pages import list_page_paths, load_page

_EMPTY = "# Index\n\n_No pages yet._\n"


def _type_heading(page_type: str) -> str:
    return page_type.replace("-", " ").title()


def build_index(cfg: WikiConfig) -> str:
    """Render index.md from page frontmatter, grouped by type. Deterministic."""
    entries: list[tuple[str, str, str, str]] = []  # (type, title, slug, summary)
    for path in list_page_paths(cfg):
        try:
            fm, _ = load_page(path)
        except Exception:
            continue  # unparseable pages are reported by lint, not cataloged here
        slug = fm.slug or path.stem
        entries.append((fm.type or "untyped", fm.title or slug, slug, fm.summary))

    if not entries:
        return _EMPTY

    order = {t: i for i, t in enumerate(PAGE_TYPES)}
    types = sorted({e[0] for e in entries}, key=lambda t: (order.get(t, len(order)), t))

    lines = ["# Index", ""]
    for t in types:
        lines.append(f"## {_type_heading(t)}")
        for _type, title, slug, summary in sorted(
            (e for e in entries if e[0] == t), key=lambda e: e[1].lower()
        ):
            lines.append(f"- [[{slug}]] — {summary.strip() if summary else '(no summary)'}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_index(cfg: WikiConfig) -> None:
    cfg.index_file.write_text(build_index(cfg), encoding="utf-8")


def index_is_current(cfg: WikiConfig) -> bool:
    return cfg.index_file.exists() and cfg.index_file.read_text(encoding="utf-8") == build_index(cfg)
