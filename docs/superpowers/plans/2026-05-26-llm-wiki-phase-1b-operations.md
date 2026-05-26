# LLM Wiki Phase 1 — Milestone B: Bookkeeping Operations Implementation Plan

> **Execution note:** Calibrated for INLINE execution by the controller (TDD, commit per task, single holistic review at the end) — lighter than Milestone A's per-task two-stage subagent review, per user request. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Implement the six deterministic, LLM-free CLI operations that make the scaffolded wiki actually work end-to-end: `add-source`, `new-page`, `index`, `log`, `search`, `lint`.

**Architecture:** One focused module per concern (`sources.py`, `pages.py`, `catalog.py`, `log.py`, `search.py`, `lint.py`), each a small set of pure-ish functions over `WikiConfig` and the filesystem. `cli.py` stays a thin dispatch layer adding one command per operation. All composition reuses Milestone A modules (`config`, `frontmatter`, `assets`). No LLM calls. Markdown remains the single source of truth.

**Tech Stack:** Python ≥3.11, Typer, PyYAML, `rank-bm25` (already declared), stdlib `urllib`/`shutil` for `add-source`, `pytest`.

**Spec reference:** Section 4 (CLI command surface + lint checks) and Section 3 (frontmatter) of `docs/superpowers/specs/2026-05-25-llm-wiki-phase-1-design.md`.

---

## Conventions used across tasks
- Every command resolves the wiki via `config.find_wiki_root(path)` then `load_config`; if none found, exit with a clear error.
- Read/inspect commands (`search`, `lint`, `index --check`) support `--json`.
- Exit codes: `0` ok, `1` error, `2` lint found error-level issues.
- Wiki-links are `[[slug]]` (optionally `[[slug|alias text]]`); resolved against page slugs + `aliases`.

---

## Task B1: Config `extra_types` + allowed-types + validate(allowed_types)

**Files:** Modify `src/llm_wiki/config.py`, `src/llm_wiki/frontmatter.py`; Test `tests/test_config.py`, `tests/test_frontmatter.py`.

- [ ] Add `extra_types: list[str] = field(default_factory=list)` to `WikiConfig`; load from `[wiki].extra_types`; serialize in `dump_config` (TOML array). Add `allowed_types` property → `tuple(PAGE_TYPES) + tuple(extra_types)` (import PAGE_TYPES from frontmatter).
- [ ] Change `frontmatter.validate(fm, allowed_types=PAGE_TYPES)` — unknown-type check uses `allowed_types`. Default keeps existing callers/tests green.
- [ ] Tests: config round-trips `extra_types`; `validate(fm, allowed_types=(...,"recipe"))` accepts a custom type; default still rejects it.

## Task B2: `pages.py` — slugify, new_page, load/list

**Files:** Create `src/llm_wiki/pages.py`; Test `tests/test_pages.py`.

- [ ] `slugify(text) -> str` (lowercase, non-alphanumeric → `-`, collapse repeats, strip).
- [ ] `list_page_paths(cfg) -> list[Path]` (sorted `*.md` in `pages/`).
- [ ] `load_page(path) -> tuple[PageFrontmatter, str]` (read + `frontmatter.parse`).
- [ ] `new_page(cfg, type, title, summary="", tags=(), sources=(), slug=None) -> Path`:
  - reject `type` not in `cfg.allowed_types` (ValueError);
  - slug = `slug or slugify(title)`; raise `FileExistsError` (with suggested `-2` slug) if `pages/<slug>.md` exists;
  - body template = `assets.load_template(page_template_name(type))` if it exists, else `""` (custom types may lack a template);
  - build `PageFrontmatter(created=today(), updated=today(), slug=slug, ...)`, write via `frontmatter.dump`. Return path.
- [ ] Tests: slugify cases; new_page writes valid parseable frontmatter with correct slug/type/dates; duplicate slug raises; unknown type raises; sources/tags persisted.

## Task B3: `catalog.py` — build/write/index_is_current

**Files:** Create `src/llm_wiki/catalog.py`; Test `tests/test_catalog.py`.

- [ ] `build_index(cfg) -> str`: if no pages → `"# Index\n\n_No pages yet._\n"`. Else group pages by `type` (types in a stable order: PAGE_TYPES first, then any others alphabetically), within a group sort by title; render:
  ```
  # Index

  ## <type>
  - [[<slug>]] — <summary or "(no summary)">
  ```
- [ ] `write_index(cfg) -> None` writes `build_index` to `index_file`.
- [ ] `index_is_current(cfg) -> bool`: `index_file` exists and its text == `build_index(cfg)`.
- [ ] Tests: empty wiki yields the seed text and `is_current` true after write; adding a page makes `is_current` false until `write_index`; grouping/ordering deterministic.

## Task B4: `log.py` — append_log

**Files:** Create `src/llm_wiki/log.py`; Test `tests/test_log.py`.

- [ ] `append_log(cfg, action, title, note=None) -> None`: append `\n## [<today>] <action> | <title>\n` to `log_file` (create with `# Log\n` header if absent). If `note`, add a `> <note>` line under it.
- [ ] Tests: appends canonical line; multiple appends accumulate in order; header created when file absent.

## Task B5: `sources.py` — add_source

**Files:** Create `src/llm_wiki/sources.py`; Test `tests/test_sources.py`.

- [ ] `add_source(cfg, src, title=None, source_id=None) -> str`:
  - is-URL if `src` starts with `http://`/`https://`.
  - id = `source_id` or `slugify(title)` or `slugify(stem of path/url)`; ensure unique in `inbox/` (suffix `-2`…). Preserve a sensible extension (local: original suffix; URL: suffix from URL path, else `.html`).
  - local file → `shutil.cop2`/`copyfile` into `inbox/<id><ext>`; URL → fetch via `urllib.request.urlopen` (timeout), write bytes atomically (temp + rename). On fetch error, raise with a clear message and write nothing.
  - if a file with that id already exists, return the existing id (idempotent), don't refetch.
  - return the id (stem, no extension) — what goes in a page's `sources:`.
- [ ] Tests: local file copied into inbox, id returned, file present; duplicate add returns same id without duplicating; URL fetch with `urlopen` monkeypatched writes the content; fetch error raises and leaves inbox clean.

## Task B6: `search.py` — BM25 + grep fallback

**Files:** Create `src/llm_wiki/search.py`; Test `tests/test_search.py`.

- [ ] `@dataclass Hit: slug, title, score, snippet`.
- [ ] `_tokenize(text) -> list[str]` (lowercase, split on non-alphanumeric, drop empties).
- [ ] `search(cfg, query, type=None, tag=None, limit=10) -> list[Hit]`:
  - collect pages (optionally filtered by `type`/`tag`); corpus doc = tokens of title+summary+tags+body;
  - rank with `rank_bm25.BM25Okapi`; if a page has zero query-term overlap its score is ~0 — keep only score > 0; sort desc; take `limit`.
  - snippet = first ~160 chars of body (whitespace-collapsed).
  - empty corpus or empty query → `[]`. (Retriever kept behind this single function so Phase 3 can add a vector leg + fusion.)
- [ ] Tests: a query term present in one page ranks it first; type/tag filters apply; no-match query → `[]`; empty wiki → `[]`.

## Task B7: `lint.py` — structural checks + safe fix

**Files:** Create `src/llm_wiki/lint.py`; Test `tests/test_lint.py`.

- [ ] `@dataclass LintIssue: level ("error"|"warning"|"info"), code, page (slug or ""), message`.
- [ ] `run_lint(cfg) -> list[LintIssue]` runs these checks (each tolerant — must NEVER crash on a bad page):
  - **bad_frontmatter** (error): a page whose `frontmatter.parse` raises (no/garbled frontmatter) → issue; otherwise run `frontmatter.validate(fm, cfg.allowed_types)` and emit each error.
  - **broken_link** (error): `[[slug]]` targets (and `related`/`supersedes`/`superseded_by`/`contradicts`) that don't resolve to an existing slug/alias.
  - **duplicate_slug** (error): two files producing the same slug.
  - **missing_source** (error): a `sources:` id with no matching `inbox/<id>.*` file.
  - **orphan** (warning): page with no inbound `[[link]]` and not in any other page's `related`.
  - **stale** (warning): `review_by` < today, or `updated` older than `cfg.stale_days`.
  - **index_stale** (warning): `not catalog.index_is_current(cfg)`.
  - **contradiction** (info): each declared `contradicts:` edge surfaced for agent review (the Phase-1 structural hook).
- [ ] `fix(cfg) -> list[LintIssue]`: safe auto-repairs only — rebuild the index (`catalog.write_index`) and normalize each parseable page (re-`dump` to fix field order/defaults). Return remaining issues from a fresh `run_lint`.
- [ ] Tests (table-driven, one per code): build a temp wiki, plant each violation, assert the code appears; a clean wiki yields no error-level issues; `fix` clears `index_stale`; bad-frontmatter page does not crash the run.

## Task B8: CLI wiring + end-to-end loop test

**Files:** Modify `src/llm_wiki/cli.py`; Test `tests/test_cli_operations.py`.

- [ ] Add a `_resolve_cfg(path) -> WikiConfig` helper (find_wiki_root + load_config; `typer.Exit(1)` with a clear message if none).
- [ ] Add commands, each thin (resolve cfg → call module → echo result / JSON):
  - `add-source <src> [--title] [--id]` → prints the id.
  - `new-page --type --title [--summary --tags --sources --slug]` → prints created path (catches FileExistsError/ValueError → exit 1 with message).
  - `index [--check]` → rebuild & write, or `--check` exits 2 if stale.
  - `log <action> <title> [--note]`.
  - `search <query> [--type --tag --limit --json]` → ranked list (or JSON).
  - `lint [--fix] [--json]` → prints issues grouped by level; exit 2 if any error-level remain.
- [ ] End-to-end test (`tests/test_cli_operations.py`): init a temp wiki, then via the CLI: `add-source` a temp file → `new-page` a source-summary referencing it → `index` → `log ingest` → `lint` exits 0 (clean) → `search` finds the page. Use Typer's `CliRunner`.
- [ ] Run the FULL suite; confirm green and that `llm-wiki --help` lists all new commands.

---

## After Milestone B
Milestone C (opt-in hooks, `doctor`/`status`, `upgrade`, broader integration tests) completes Phase 1.
