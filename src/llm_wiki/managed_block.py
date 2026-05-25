from __future__ import annotations

import re
from pathlib import Path

BEGIN = "<!-- BEGIN llm-wiki (managed) -->"
END = "<!-- END llm-wiki (managed) -->"

_PATTERN = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.DOTALL)


def render_block(target: str, wiki_rel: str) -> str:
    """Render the managed block. `wiki_rel` is "" (root mode) or "wiki/"."""
    schema_ref = f"@{wiki_rel}SCHEMA.md" if target == "claude" else f"`{wiki_rel}SCHEMA.md`"
    body = f"""## LLM Wiki
This project maintains an LLM wiki under `{wiki_rel or "./"}` via the `llm-wiki` CLI.
Full maintainer rules: {schema_ref}

Invariants — do not violate:
- `{wiki_rel}index.md` and `{wiki_rel}log.md` are GENERATED. Never hand-edit; use `llm-wiki index` / `llm-wiki log`.
- `{wiki_rel}inbox/` is read-only raw sources. Add only via `llm-wiki add-source`.
- Create pages with `llm-wiki new-page` (correct frontmatter), never by hand.
- Before creating a page, `llm-wiki search` first — update an existing page rather than duplicate.
- After any wiki change, run `llm-wiki lint` (then `llm-wiki index`).

Maintain the wiki only when explicitly asked (e.g. /wiki-ingest, /wiki-query, /wiki-lint).
See {schema_ref} for the full ingest/query/lint workflows."""
    return f"{BEGIN}\n{body}\n{END}\n"


def upsert_block(file_path: Path, block: str) -> None:
    existing = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
    if _PATTERN.search(existing):
        new = _PATTERN.sub(block, existing)
    elif existing == "":
        new = block
    else:
        sep = "\n" if existing.endswith("\n") else "\n\n"
        new = existing + sep + block
    file_path.write_text(new, encoding="utf-8")
