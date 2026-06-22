from __future__ import annotations

import re
from pathlib import Path

BEGIN = "<!-- BEGIN autowiki (managed) -->"
END = "<!-- END autowiki (managed) -->"

_PATTERN = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.DOTALL)


def render_block(target: str, wiki_rel: str) -> str:
    """Render the managed block. `wiki_rel` is "" (root mode) or "wiki/"."""
    schema_ref = f"@{wiki_rel}SCHEMA.md" if target == "claude" else f"`{wiki_rel}SCHEMA.md`"
    body = f"""## LLM Wiki
This project maintains an LLM wiki under `{wiki_rel or "./"}` via the `autowiki` CLI.
Full maintainer rules: {schema_ref}

Invariants — do not violate:
- `{wiki_rel}index.md` and `{wiki_rel}log.md` are GENERATED. Never hand-edit; use `autowiki index` / `autowiki log`.
- `{wiki_rel}inbox/` is read-only raw sources. Add only via `autowiki add-source`.
- Create pages with `autowiki new-page` (correct frontmatter), never by hand.
- Before creating a page, `autowiki search` first — update an existing page rather than duplicate.
- After any wiki change, run `autowiki lint` (then `autowiki index`).

Don't modify the wiki unprompted — act on it only when asked (/wiki-ingest,
/wiki-query, /wiki-lint). BUT lean proactive about *suggesting* it: whenever
substantial work takes shape — a PR opened, a PR or feature branch merged (to main
or locally), or a meaningful unit of work finished — offer a /wiki-ingest so the
change is captured. Always suggest on a merge; suggest on a PR open too. The user
decides whether to run it.
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
