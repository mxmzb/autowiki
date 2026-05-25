# LLM Wiki Phase 1 — Milestone A: Foundation & `init` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `llm-wiki` Python package toolchain and a working `llm-wiki init` that scaffolds a Karpathy-style LLM wiki (the `wiki/` tree, config, `SCHEMA.md`, managed block, and Claude slash commands) into any new or existing project, plus a `version` command.

**Architecture:** A `uv`-managed Python package with a thin Typer CLI (`cli.py`) that dispatches to focused single-responsibility modules. `init` is the only user-facing command in this milestone; it composes pure functions (config I/O, template loading, managed-block injection) that are unit-tested directly. The full forward-compatible frontmatter schema is defined now (validated but mostly inert) so later milestones/phases need no migration. All bookkeeping is deterministic and LLM-free.

**Tech Stack:** Python ≥3.11 (stdlib `tomllib`), Typer (CLI), PyYAML (frontmatter), `rank-bm25` (declared now, used in Milestone B), `pytest` (tests), `uv` (env + global install).

---

## Spec reference

Implements Section 1 (architecture), Section 2 (layout + `init`), Section 3 (frontmatter schema), and the `SCHEMA.md`/managed-block/slash-command pieces of Section 5 from
`docs/superpowers/specs/2026-05-25-llm-wiki-phase-1-design.md`.

**Out of scope for Milestone A** (later milestones): `add-source`, `new-page`, `index`, `log`, `search`, `lint`, `doctor`, `status`, `upgrade`, hooks (`--hooks` flag + `hooks.py`). `init` here ships **without** `--hooks`; that flag is added in Milestone C alongside `hooks.py`.

## File structure (Milestone A)

| File | Responsibility |
|---|---|
| `pyproject.toml` | package metadata, deps, `llm-wiki` entry point, build config |
| `src/llm_wiki/__init__.py` | package marker + `__version__` |
| `src/llm_wiki/cli.py` | thin Typer app: `version`, `init` (dispatch only) |
| `src/llm_wiki/config.py` | `WikiConfig`, root discovery (walk-up), TOML read/write |
| `src/llm_wiki/frontmatter.py` | full frontmatter dataclass, parse/dump, validate, `today()` |
| `src/llm_wiki/assets.py` | load packaged templates from `templates/` |
| `src/llm_wiki/managed_block.py` | render + idempotent upsert of the CLAUDE.md/AGENTS.md block |
| `src/llm_wiki/scaffold.py` | `init_wiki()` — create tree, seed files, config, block, commands |
| `src/llm_wiki/templates/SCHEMA.md` | maintainer playbook (data asset) |
| `src/llm_wiki/templates/page_*.md` | per-type page body templates (data assets) |
| `src/llm_wiki/templates/command_wiki-*.md` | Claude slash-command prompt files (data assets) |
| `tests/conftest.py` | pytest fixtures (`project` tmp dir) |
| `tests/test_*.py` | one test module per source module |

---

## Task 1: Project setup & `version` command

**Files:**
- Create: `pyproject.toml`
- Create: `src/llm_wiki/__init__.py`
- Create: `src/llm_wiki/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "llm-wiki"
version = "0.1.0"
description = "Initialize and maintain Karpathy-style LLM wikis in any project."
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "pyyaml>=6.0",
    "rank-bm25>=0.2.2",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
llm-wiki = "llm_wiki.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/llm_wiki"]

[tool.hatch.build.targets.wheel.force-include]
"src/llm_wiki/templates" = "llm_wiki/templates"
```

- [ ] **Step 2: Create the package files**

`src/llm_wiki/__init__.py`:
```python
__version__ = "0.1.0"
```

`src/llm_wiki/cli.py`:
```python
from __future__ import annotations

import typer

from . import __version__

SCHEMA_VERSION = 1

app = typer.Typer(
    help="Initialize and maintain Karpathy-style LLM wikis.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def version() -> None:
    """Print the llm-wiki tool and schema version."""
    typer.echo(f"llm-wiki {__version__} (schema v{SCHEMA_VERSION})")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write the failing test**

`tests/test_cli.py`:
```python
from typer.testing import CliRunner

from llm_wiki.cli import app

runner = CliRunner()


def test_version_prints_tool_and_schema_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "llm-wiki" in result.stdout
    assert "schema v" in result.stdout
```

- [ ] **Step 4: Set up the environment and run the test (expect FAIL → then PASS)**

```bash
uv venv
uv pip install -e ".[dev]"
uv run pytest tests/test_cli.py -v
```
Expected: PASS (`test_version_prints_tool_and_schema_version`). If `uv` resolves before the package builds, re-run the last line.

- [ ] **Step 5: Verify the console script works**

```bash
uv run llm-wiki version
```
Expected output contains: `llm-wiki 0.1.0 (schema v1)`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/llm_wiki/__init__.py src/llm_wiki/cli.py tests/test_cli.py
git commit -m "feat: package skeleton with version command"
```

---

## Task 2: Config & wiki-root discovery

**Files:**
- Create: `src/llm_wiki/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:
```python
from pathlib import Path

from llm_wiki.config import (
    CONFIG_NAME,
    WikiConfig,
    find_wiki_root,
    load_config,
    write_config,
)


def test_find_wiki_root_walks_up(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "pages").mkdir(parents=True)
    (wiki / CONFIG_NAME).write_text("[wiki]\nschema_version = 1\n")
    deep = wiki / "pages"
    assert find_wiki_root(deep) == wiki


def test_find_wiki_root_returns_none_when_absent(tmp_path: Path):
    assert find_wiki_root(tmp_path) is None


def test_config_round_trip(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    cfg = WikiConfig(root=wiki, target="generic", stale_days=30)
    write_config(cfg)
    loaded = load_config(wiki)
    assert loaded.target == "generic"
    assert loaded.stale_days == 30
    assert loaded.schema_version == 1


def test_config_path_helpers(tmp_path: Path):
    cfg = WikiConfig(root=tmp_path / "wiki")
    assert cfg.pages_dir.name == "pages"
    assert cfg.inbox_dir.name == "inbox"
    assert cfg.index_file.name == "index.md"
    assert cfg.log_file.name == "log.md"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: llm_wiki.config`)

- [ ] **Step 3: Implement `config.py`**

```python
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_NAME = ".llm-wiki.toml"
SCHEMA_VERSION = 1


@dataclass
class WikiConfig:
    root: Path  # dir containing pages/, inbox/, index.md, log.md, SCHEMA.md
    schema_version: int = SCHEMA_VERSION
    target: str = "claude"  # "claude" | "generic"
    embedding_provider: str = "local"
    stale_days: int = 365

    @property
    def pages_dir(self) -> Path:
        return self.root / "pages"

    @property
    def inbox_dir(self) -> Path:
        return self.root / "inbox"

    @property
    def index_file(self) -> Path:
        return self.root / "index.md"

    @property
    def log_file(self) -> Path:
        return self.root / "log.md"

    @property
    def schema_file(self) -> Path:
        return self.root / "SCHEMA.md"

    @property
    def index_dir(self) -> Path:
        return self.root / ".index"

    @property
    def config_file(self) -> Path:
        return self.root / CONFIG_NAME


def find_wiki_root(start: Path) -> Path | None:
    start = start.resolve()
    for d in (start, *start.parents):
        if (d / CONFIG_NAME).is_file():
            return d
    return None


def load_config(root: Path) -> WikiConfig:
    data = tomllib.loads((root / CONFIG_NAME).read_text(encoding="utf-8"))
    wiki = data.get("wiki", {})
    return WikiConfig(
        root=root,
        schema_version=wiki.get("schema_version", SCHEMA_VERSION),
        target=wiki.get("target", "claude"),
        embedding_provider=wiki.get("embedding_provider", "local"),
        stale_days=wiki.get("stale_days", 365),
    )


def dump_config(cfg: WikiConfig) -> str:
    return (
        "[wiki]\n"
        f"schema_version = {cfg.schema_version}\n"
        f'target = "{cfg.target}"\n'
        f'embedding_provider = "{cfg.embedding_provider}"\n'
        f"stale_days = {cfg.stale_days}\n"
    )


def write_config(cfg: WikiConfig) -> None:
    cfg.config_file.write_text(dump_config(cfg), encoding="utf-8")
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/config.py tests/test_config.py
git commit -m "feat: wiki config and root discovery"
```

---

## Task 3: Frontmatter schema (the v2-ready seam)

**Files:**
- Create: `src/llm_wiki/frontmatter.py`
- Test: `tests/test_frontmatter.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_frontmatter.py`:
```python
from llm_wiki.frontmatter import (
    PAGE_TYPES,
    PageFrontmatter,
    dump,
    parse,
    today,
    validate,
)


def test_full_schema_defaults_present():
    fm = PageFrontmatter(title="X", type="entity", created="2026-05-25", updated="2026-05-25")
    assert fm.status == "active"
    assert fm.tier == "semantic"
    assert fm.confidence is None
    assert fm.tags == [] and fm.related == [] and fm.entities == []


def test_dump_then_parse_round_trip():
    fm = PageFrontmatter(
        title="Andrej Karpathy",
        type="entity",
        created="2026-05-25",
        updated="2026-05-25",
        slug="andrej-karpathy",
        summary="ML researcher",
        tags=["ml", "people"],
        related=["llm-wiki-pattern"],
    )
    text = dump(fm, "Body paragraph.\n")
    parsed, body = parse(text)
    assert parsed == fm
    assert body.strip() == "Body paragraph."


def test_parse_tolerates_unknown_fields():
    text = "---\ntitle: X\ntype: note\ncreated: '2026-05-25'\nupdated: '2026-05-25'\nbogus: 1\n---\nbody\n"
    fm, _ = parse(text)
    assert fm.title == "X"


def test_validate_reports_missing_required_and_bad_enums():
    fm = PageFrontmatter(title="", type="widget", created="", updated="2026-05-25")
    errors = validate(fm)
    assert any("title" in e for e in errors)
    assert any("created" in e for e in errors)
    assert any("widget" in e for e in errors)


def test_validate_clean_page_has_no_errors():
    fm = PageFrontmatter(title="X", type="concept", created=today(), updated=today())
    assert validate(fm) == []


def test_page_types_constant():
    assert "source-summary" in PAGE_TYPES and "note" in PAGE_TYPES
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_frontmatter.py -v`
Expected: FAIL (`ModuleNotFoundError: llm_wiki.frontmatter`)

- [ ] **Step 3: Implement `frontmatter.py`**

```python
from __future__ import annotations

import dataclasses
import datetime as dt
from dataclasses import asdict, dataclass, field

import yaml

PAGE_TYPES = ("source-summary", "entity", "concept", "note")
STATUSES = ("active", "draft", "deprecated", "superseded")
TIERS = ("working", "episodic", "semantic", "procedural")
FM_DELIM = "---"


@dataclass
class PageFrontmatter:
    # Required (defaulted to "" so parse never crashes; validate() enforces non-empty)
    title: str = ""
    type: str = ""
    created: str = ""
    updated: str = ""
    # v1 active fields
    slug: str = ""
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    # v2-ready seam (validated for shape, behavior lands in later phases)
    status: str = "active"
    confidence: float | None = None
    review_by: str | None = None
    supersedes: list[str] = field(default_factory=list)
    superseded_by: list[str] = field(default_factory=list)
    contradicts: list[str] = field(default_factory=list)
    tier: str = "semantic"
    entities: list[dict] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)


_FIELDS = {f.name for f in dataclasses.fields(PageFrontmatter)}


def today() -> str:
    return dt.date.today().isoformat()


def parse(text: str) -> tuple[PageFrontmatter, str]:
    if not text.startswith(FM_DELIM):
        raise ValueError("page is missing YAML frontmatter")
    _, fm_block, body = text.split(FM_DELIM, 2)
    data = yaml.safe_load(fm_block) or {}
    known = {k: v for k, v in data.items() if k in _FIELDS}
    return PageFrontmatter(**known), body.lstrip("\n")


def dump(fm: PageFrontmatter, body: str) -> str:
    fm_yaml = yaml.safe_dump(asdict(fm), sort_keys=False, allow_unicode=True).strip()
    return f"{FM_DELIM}\n{fm_yaml}\n{FM_DELIM}\n\n{body.rstrip()}\n"


def validate(fm: PageFrontmatter) -> list[str]:
    errors: list[str] = []
    for req in ("title", "type", "created", "updated"):
        if not getattr(fm, req):
            errors.append(f"missing required field: {req}")
    if fm.type and fm.type not in PAGE_TYPES:
        errors.append(f"unknown type: {fm.type}")
    if fm.status not in STATUSES:
        errors.append(f"invalid status: {fm.status}")
    if fm.tier not in TIERS:
        errors.append(f"invalid tier: {fm.tier}")
    if fm.confidence is not None and not (0.0 <= float(fm.confidence) <= 1.0):
        errors.append("confidence must be between 0 and 1")
    return errors
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_frontmatter.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/frontmatter.py tests/test_frontmatter.py
git commit -m "feat: forward-compatible page frontmatter schema"
```

---

## Task 4: Packaged templates & loader

**Files:**
- Create: `src/llm_wiki/templates/SCHEMA.md`
- Create: `src/llm_wiki/templates/page_source-summary.md`
- Create: `src/llm_wiki/templates/page_entity.md`
- Create: `src/llm_wiki/templates/page_concept.md`
- Create: `src/llm_wiki/templates/page_note.md`
- Create: `src/llm_wiki/templates/command_wiki-ingest.md`
- Create: `src/llm_wiki/templates/command_wiki-query.md`
- Create: `src/llm_wiki/templates/command_wiki-lint.md`
- Create: `src/llm_wiki/assets.py`
- Test: `tests/test_assets.py`

- [ ] **Step 1: Create `src/llm_wiki/templates/SCHEMA.md`**

```markdown
# LLM Wiki — Maintainer Schema

This file tells you (the agent) how to maintain this wiki. It is the operating manual.
All structural bookkeeping is done by the `llm-wiki` CLI; you do the reading and writing.

## Layers
- `inbox/` — raw, human-curated sources. **Read-only.** Add only via `llm-wiki add-source`.
- `pages/` — the wiki you own: `entity`, `concept`, `source-summary`, and `note` pages.
- `index.md` / `log.md` — **generated**. Never hand-edit; use `llm-wiki index` / `llm-wiki log`.

## Invariants
1. Create pages with `llm-wiki new-page` so frontmatter is correct. Never hand-write a new page file.
2. Before creating a page, run `llm-wiki search "<topic>"` — prefer updating an existing page over duplicating.
3. After any change to `pages/`, run `llm-wiki index` then `llm-wiki lint` and fix what it reports.
4. Cross-link generously with `[[slug]]` wiki-links and mirror important links in the `related:` frontmatter list.

## Page types
- `entity` — a person, project, library, org, or place (a "noun").
- `concept` — an idea, topic, or theme.
- `source-summary` — a summary of one ingested source; set its `sources:` to the inbox id.
- `note` — a crystallized answer to a query or a cross-cutting synthesis.

## Frontmatter
Required: `title`, `type`, `created`, `updated`. Set by `new-page`; update `updated` when you edit.
Useful now: `summary` (one line, shown in `index.md`), `tags`, `aliases`, `sources`, `related`.
Reserved (leave defaults unless you know them): `status`, `confidence`, `review_by`,
`supersedes`, `superseded_by`, `contradicts`, `tier`, `entities`, `relations`.

## Workflows

### Ingest a source
1. `llm-wiki add-source <path|url>` → note the returned source id.
2. Read the source. Identify the entities, concepts, and key claims.
3. Discuss findings with the user (skip if running non-interactively).
4. `llm-wiki new-page --type source-summary --title "..." --sources <id>` and write the summary.
5. For each entity/concept: `llm-wiki search` first; update the existing page or `llm-wiki new-page`. Add `[[links]]`.
6. `llm-wiki index` → `llm-wiki log ingest "<title>"` → `llm-wiki lint` (fix issues).

### Answer a query
1. `llm-wiki search "<question>"`; read the top pages.
2. Synthesize an answer with `[[links]]` to your sources.
3. If the answer is reusable, `llm-wiki new-page --type note`, write it, then `llm-wiki index` and `llm-wiki log query "<question>"`.

### Lint
1. `llm-wiki lint --json`; read the issues.
2. Fix broken links, orphans, missing summaries, and stale pages. Re-run `llm-wiki lint` until clean.

## Customizing your wiki
This file is yours to edit. To adapt the wiki to your use case:
- **Add a page type:** describe it here under "Page types" and use `llm-wiki new-page --type <yourtype>`
  (add it to `[wiki].extra_types` in `.llm-wiki.toml` so lint accepts it).
- **Change the stale threshold:** set `stale_days` in `.llm-wiki.toml`.
- **Change conventions:** edit the rules above; the CLI enforces structure, this file guides judgement.
```

- [ ] **Step 2: Create the four page body templates**

`src/llm_wiki/templates/page_entity.md`:
```markdown
## Overview

## Key facts

## Relationships

## Sources
```

`src/llm_wiki/templates/page_concept.md`:
```markdown
## Definition

## Why it matters

## Related concepts

## Sources
```

`src/llm_wiki/templates/page_source-summary.md`:
```markdown
## Summary

## Key points

## Entities & concepts

## Notes
```

`src/llm_wiki/templates/page_note.md`:
```markdown
## Question

## Answer

## Supporting pages
```

- [ ] **Step 3: Create the three slash-command templates**

`src/llm_wiki/templates/command_wiki-ingest.md`:
```markdown
---
description: Ingest a source into the LLM wiki
argument-hint: <path-or-url>
---

Ingest the source `$ARGUMENTS` into the wiki, following the **Ingest a source** workflow in @wiki/SCHEMA.md.

Steps:
1. Run `llm-wiki add-source $ARGUMENTS` and note the source id.
2. Read the source; identify entities, concepts, and key claims; briefly discuss findings with me.
3. Create a `source-summary` page with `llm-wiki new-page`, then create/update entity and concept pages
   (run `llm-wiki search` first to avoid duplicates). Cross-link with `[[slug]]`.
4. Run `llm-wiki index`, then `llm-wiki log ingest "<title>"`, then `llm-wiki lint` and fix anything reported.
```

`src/llm_wiki/templates/command_wiki-query.md`:
```markdown
---
description: Query the LLM wiki and optionally crystallize a note
argument-hint: <question>
---

Answer the question `$ARGUMENTS` using the wiki, following the **Answer a query** workflow in @wiki/SCHEMA.md.

Steps:
1. Run `llm-wiki search "$ARGUMENTS"` and read the top pages.
2. Synthesize an answer with `[[slug]]` citations to the pages you used.
3. If the answer is reusable, create a `note` page with `llm-wiki new-page`, then run `llm-wiki index`
   and `llm-wiki log query "$ARGUMENTS"`.
```

`src/llm_wiki/templates/command_wiki-lint.md`:
```markdown
---
description: Lint the LLM wiki and fix issues
---

Run the **Lint** workflow in @wiki/SCHEMA.md.

Steps:
1. Run `llm-wiki lint --json` and read the reported issues.
2. Fix broken links, orphans, missing summaries, and stale pages. For flagged contradictions, read the
   pages and resolve or annotate them.
3. Re-run `llm-wiki lint` until it is clean.
```

- [ ] **Step 4: Write the failing test**

`tests/test_assets.py`:
```python
from llm_wiki.assets import load_template, page_template_name
from llm_wiki.frontmatter import PAGE_TYPES


def test_load_schema_template_nonempty():
    text = load_template("SCHEMA.md")
    assert "Maintainer Schema" in text


def test_every_page_type_has_a_template():
    for t in PAGE_TYPES:
        text = load_template(page_template_name(t))
        assert text.strip() != ""


def test_slash_command_templates_exist():
    for name in ("wiki-ingest", "wiki-query", "wiki-lint"):
        text = load_template(f"command_{name}.md")
        assert "llm-wiki" in text
```

- [ ] **Step 5: Run to verify failure**

Run: `uv run pytest tests/test_assets.py -v`
Expected: FAIL (`ModuleNotFoundError: llm_wiki.assets`)

- [ ] **Step 6: Implement `assets.py`**

```python
from __future__ import annotations

from importlib.resources import files


def load_template(name: str) -> str:
    """Read a packaged template asset from llm_wiki/templates/."""
    resource = files("llm_wiki").joinpath("templates", name)
    return resource.read_text(encoding="utf-8")


def page_template_name(page_type: str) -> str:
    return f"page_{page_type}.md"
```

- [ ] **Step 7: Run to verify pass**

Run: `uv run pytest tests/test_assets.py -v`
Expected: PASS (3 tests)

- [ ] **Step 8: Commit**

```bash
git add src/llm_wiki/templates src/llm_wiki/assets.py tests/test_assets.py
git commit -m "feat: packaged schema, page, and slash-command templates"
```

---

## Task 5: Managed-block injection

**Files:**
- Create: `src/llm_wiki/managed_block.py`
- Test: `tests/test_managed_block.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_managed_block.py`:
```python
from pathlib import Path

from llm_wiki.managed_block import BEGIN, END, render_block, upsert_block


def test_render_block_claude_uses_import():
    block = render_block("claude", "wiki/")
    assert "@wiki/SCHEMA.md" in block
    assert BEGIN in block and END in block


def test_render_block_generic_uses_plain_pointer():
    block = render_block("generic", "wiki/")
    assert "@wiki/SCHEMA.md" not in block
    assert "wiki/SCHEMA.md" in block


def test_upsert_creates_file_and_preserves_existing_content(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("# My Project\n\nExisting notes.\n")
    upsert_block(f, render_block("claude", "wiki/"))
    text = f.read_text()
    assert "# My Project" in text
    assert "Existing notes." in text
    assert BEGIN in text


def test_upsert_is_idempotent(tmp_path: Path):
    f = tmp_path / "CLAUDE.md"
    block = render_block("claude", "wiki/")
    upsert_block(f, block)
    first = f.read_text()
    upsert_block(f, block)
    assert f.read_text() == first


def test_upsert_replaces_old_block(tmp_path: Path):
    f = tmp_path / "AGENTS.md"
    upsert_block(f, render_block("generic", "wiki/"))
    upsert_block(f, render_block("generic", "docs/"))
    text = f.read_text()
    assert text.count(BEGIN) == 1
    assert "docs/SCHEMA.md" in text
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_managed_block.py -v`
Expected: FAIL (`ModuleNotFoundError: llm_wiki.managed_block`)

- [ ] **Step 3: Implement `managed_block.py`**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_managed_block.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/llm_wiki/managed_block.py tests/test_managed_block.py
git commit -m "feat: idempotent managed-block injection for CLAUDE.md/AGENTS.md"
```

---

## Task 6: `init_wiki` scaffolding + `init` CLI command

**Files:**
- Create: `src/llm_wiki/scaffold.py`
- Modify: `src/llm_wiki/cli.py` (add `init` command)
- Create: `tests/conftest.py`
- Test: `tests/test_scaffold.py`

- [ ] **Step 1: Create the shared fixture**

`tests/conftest.py`:
```python
from pathlib import Path

import pytest


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A clean temporary project directory."""
    return tmp_path
```

- [ ] **Step 2: Write the failing tests**

`tests/test_scaffold.py`:
```python
from pathlib import Path

from llm_wiki.config import CONFIG_NAME, load_config
from llm_wiki.managed_block import BEGIN
from llm_wiki.scaffold import init_wiki


def test_init_creates_expected_tree(project: Path):
    cfg, action = init_wiki(project, target="claude")
    assert action == "created"
    wiki = project / "wiki"
    for rel in ("inbox", "pages", "index.md", "log.md", "SCHEMA.md", CONFIG_NAME, ".gitignore"):
        assert (wiki / rel).exists(), rel
    assert (wiki / "inbox" / ".gitkeep").exists()
    assert (wiki / "pages" / ".gitkeep").exists()
    assert (wiki / ".gitignore").read_text().strip() == ".index/"
    assert "init | wiki initialized" in (wiki / "log.md").read_text()


def test_init_claude_target_writes_block_and_commands(project: Path):
    init_wiki(project, target="claude")
    assert BEGIN in (project / "CLAUDE.md").read_text()
    for name in ("wiki-ingest", "wiki-query", "wiki-lint"):
        assert (project / ".claude" / "commands" / f"{name}.md").exists()


def test_init_generic_target_writes_agents_md_no_commands(project: Path):
    init_wiki(project, target="generic")
    assert BEGIN in (project / "AGENTS.md").read_text()
    assert not (project / ".claude").exists()


def test_init_stores_target_in_config(project: Path):
    init_wiki(project, target="generic")
    assert load_config(project / "wiki").target == "generic"


def test_init_root_mode_places_files_at_root(project: Path):
    init_wiki(project, target="generic", root_mode=True)
    assert (project / CONFIG_NAME).exists()
    assert (project / "pages").exists()
    assert not (project / "wiki").exists()


def test_reinit_is_idempotent_and_preserves_log(project: Path):
    init_wiki(project, target="claude")
    log_before = (project / "wiki" / "log.md").read_text()
    (project / "CLAUDE.md").write_text(
        (project / "CLAUDE.md").read_text() + "\nUser added line.\n"
    )
    cfg, action = init_wiki(project, target="claude")
    assert action == "updated"
    assert (project / "wiki" / "log.md").read_text() == log_before  # log not reseeded
    assert "User added line." in (project / "CLAUDE.md").read_text()  # user content kept
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_scaffold.py -v`
Expected: FAIL (`ModuleNotFoundError: llm_wiki.scaffold`)

- [ ] **Step 4: Implement `scaffold.py`**

```python
from __future__ import annotations

from pathlib import Path

from . import config as cfgmod
from .assets import load_template
from .config import WikiConfig
from .frontmatter import today
from .managed_block import render_block, upsert_block

_SLASH_COMMANDS = ("wiki-ingest", "wiki-query", "wiki-lint")


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


def _write_if_absent(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _write_managed_block(project_root: Path, cfg: WikiConfig, root_mode: bool) -> None:
    wiki_rel = "" if root_mode else "wiki/"
    block = render_block(cfg.target, wiki_rel)
    fname = "CLAUDE.md" if cfg.target == "claude" else "AGENTS.md"
    upsert_block(project_root / fname, block)


def init_wiki(
    project_root: Path,
    target: str = "claude",
    root_mode: bool = False,
    force: bool = False,
) -> tuple[WikiConfig, str]:
    """Scaffold a wiki. Returns (config, action) where action is created|recreated|updated."""
    project_root = Path(project_root).resolve()
    wiki_root = project_root if root_mode else project_root / "wiki"
    existed = (wiki_root / cfgmod.CONFIG_NAME).exists()

    if existed and not force:
        cfg = cfgmod.load_config(wiki_root)
        _write_managed_block(project_root, cfg, root_mode)
        return cfg, "updated"

    (wiki_root / "inbox").mkdir(parents=True, exist_ok=True)
    (wiki_root / "pages").mkdir(parents=True, exist_ok=True)
    (wiki_root / ".index").mkdir(parents=True, exist_ok=True)
    _touch(wiki_root / "inbox" / ".gitkeep")
    _touch(wiki_root / "pages" / ".gitkeep")

    cfg = WikiConfig(root=wiki_root, target=target)
    cfgmod.write_config(cfg)
    (wiki_root / "SCHEMA.md").write_text(load_template("SCHEMA.md"), encoding="utf-8")
    (wiki_root / ".gitignore").write_text(".index/\n", encoding="utf-8")
    _write_if_absent(wiki_root / "index.md", "# Index\n\n_No pages yet._\n")
    _write_if_absent(
        wiki_root / "log.md", f"# Log\n\n## [{today()}] init | wiki initialized\n"
    )

    _write_managed_block(project_root, cfg, root_mode)

    if target == "claude":
        cmd_dir = project_root / ".claude" / "commands"
        cmd_dir.mkdir(parents=True, exist_ok=True)
        for name in _SLASH_COMMANDS:
            (cmd_dir / f"{name}.md").write_text(
                load_template(f"command_{name}.md"), encoding="utf-8"
            )

    return cfg, ("recreated" if existed else "created")


def resolve_target(project_root: Path, target: str, assume_yes: bool) -> str:
    """Resolve --target auto into claude|generic by detecting project conventions."""
    if target in ("claude", "generic"):
        return target
    has_claude = (project_root / ".claude").exists() or (project_root / "CLAUDE.md").exists()
    has_agents = (project_root / "AGENTS.md").exists()
    if has_claude:
        return "claude"
    if has_agents:
        return "generic"
    return "claude" if assume_yes else "claude"
```

(Note: `resolve_target` returns `claude` as the no-signal default; interactive prompting is intentionally omitted in this milestone — the CLI passes `--yes` semantics through and defaults to `claude`.)

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_scaffold.py -v`
Expected: PASS (6 tests)

- [ ] **Step 6: Add the `init` command to `cli.py`**

Insert into `src/llm_wiki/cli.py` (after the `version` command, before `def main`):
```python
from pathlib import Path  # add to imports at top of file

from .scaffold import init_wiki, resolve_target  # add to imports at top of file


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Project directory to initialize."),
    target: str = typer.Option("auto", help="auto|claude|generic"),
    root: bool = typer.Option(False, "--root", help="Place the wiki at the project root."),
    force: bool = typer.Option(False, "--force", help="Re-scaffold over an existing wiki."),
    yes: bool = typer.Option(False, "--yes", help="Non-interactive."),
) -> None:
    """Initialize an LLM wiki in PATH (new or existing project)."""
    resolved = resolve_target(path, target, yes)
    cfg, action = init_wiki(path, target=resolved, root_mode=root, force=force)
    typer.echo(f"Wiki {action} at {cfg.root} (target: {cfg.target})")
```

(Move the two new `import` lines to the top import block alongside the existing `import typer`.)

- [ ] **Step 7: Add a CLI-level smoke test**

Append to `tests/test_cli.py`:
```python
from pathlib import Path


def test_init_command_creates_wiki(tmp_path: Path):
    result = runner.invoke(app, ["init", str(tmp_path), "--target", "generic"])
    assert result.exit_code == 0
    assert (tmp_path / "wiki" / "SCHEMA.md").exists()
    assert "Wiki created" in result.stdout
```

- [ ] **Step 8: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS (all tests across every module)

- [ ] **Step 9: Verify the real command end-to-end**

```bash
cd "$(mktemp -d)" && uv run --project "$OLDPWD" llm-wiki init . --target claude && ls wiki && cat CLAUDE.md && cd - >/dev/null
```
Expected: `wiki/` tree exists; `CLAUDE.md` contains the managed block; `.claude/commands/` has three files.

- [ ] **Step 10: Commit**

```bash
git add src/llm_wiki/scaffold.py src/llm_wiki/cli.py tests/conftest.py tests/test_scaffold.py tests/test_cli.py
git commit -m "feat: llm-wiki init scaffolds the wiki tree, config, block, and commands"
```

---

## Task 7: Editable global install (dev ergonomics)

**Files:** none (verification task)

- [ ] **Step 1: Install globally as an editable tool**

```bash
uv tool install --editable .
```
Expected: installs `llm-wiki` onto PATH; edits to the source take effect without reinstall.

- [ ] **Step 2: Verify from an arbitrary directory**

```bash
cd "$(mktemp -d)" && llm-wiki version && llm-wiki init . --target generic && ls wiki && cd - >/dev/null
```
Expected: `version` prints; `init` scaffolds `wiki/` with `AGENTS.md` managed block and no `.claude/`.

- [ ] **Step 3: Document it in the README**

Create `README.md`:
```markdown
# llm-wiki

Initialize and maintain Karpathy-style LLM wikis in any project.

## Install (local dev)
```
uv tool install --editable .
```

## Usage
```
llm-wiki init [PATH] [--target claude|generic|auto] [--root]
llm-wiki version
```

`init` scaffolds a `wiki/` directory (`inbox/` sources, `pages/`, generated `index.md`/`log.md`,
`SCHEMA.md`) and injects a managed block into `CLAUDE.md`/`AGENTS.md`. See
`docs/superpowers/specs/2026-05-25-llm-wiki-phase-1-design.md` for the full design.
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README with install and usage"
```

---

## Self-review (completed by plan author)

**Spec coverage (Milestone A slice):** Section 1 architecture → reflected in module split + LLM-free design. Section 2 layout/`init` → Task 6 (tree, config, `.gitignore`, managed block, commands, `--root`, idempotent re-init); `--hooks` explicitly deferred to Milestone C. Section 3 frontmatter → Task 3 (full schema + validate). Section 5 `SCHEMA.md`/managed block/slash commands → Tasks 4–6. `version` (Section 4) → Task 1. Deferred verbs (`add-source`/`new-page`/`index`/`log`/`search`/`lint`/`doctor`/`status`/`upgrade`) are Milestones B/C and are intentionally absent here.

**Placeholder scan:** no TBD/TODO; every code step shows complete, runnable code; the `resolve_target` no-signal default is explicitly documented, not hand-waved.

**Type consistency:** `WikiConfig` fields/properties used in Task 6 match Task 2. `init_wiki(...) -> tuple[WikiConfig, str]` return shape matches its callers (cli `init`, tests). `render_block(target, wiki_rel)` / `upsert_block(path, block)` signatures match Task 5 definitions and Task 6 calls. `load_template(name)` / `page_template_name(type)` match Task 4. `PAGE_TYPES` shared between `frontmatter.py` and the asset test.

---

## After this milestone

Milestone B (operations: `add-source`, `new-page`, `index`, `log`, `search`, `lint`) and Milestone C (hooks, `doctor`/`status`, `upgrade`, integration tests) will each be written as their own plan once this one is built and green.
