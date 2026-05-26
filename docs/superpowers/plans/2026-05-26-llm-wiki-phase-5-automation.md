# LLM Wiki Phase 5 — Automation & Quality Implementation Plan

> **Execution note:** Inline TDD by the controller, commit per task, single holistic review at the end. **Final phase.**

**Goal:** Close the loop so the wiki proactively tells the in-session agent what to do — track which `inbox/` sources are still pending ingestion, surface them (+ review/lint) via a SessionStart hook, add a deterministic `maintain` pass and a `quality` score. **No LLM in the CLI** — the local Claude session does all semantic work (ingest, contradiction resolution) via existing workflows. B-mode (headless `--llm` driver) is explicitly out of scope.

**Design (approved):** "ingested" is derived, not stored: a source in `inbox/` is ingested once some page lists its id in `sources:`; otherwise it's **pending**. Quality scoring is report-only (does not gate search/index). The SessionStart proactive hook is opt-in (part of the hook set).

**Tech Stack:** Python ≥3.11, Typer, pytest. (Reuses lifecycle/lint/catalog/sources.)

---

## Task P5.1: source ingestion tracking

**Files:** Modify `src/llm_wiki/sources.py`, `src/llm_wiki/cli.py`, `src/llm_wiki/doctor.py` (status); Test `tests/test_sources.py`, `tests/test_cli_sources.py`.

- [ ] `sources.py`: `inbox_ids(cfg) -> set[str]` (inbox file stems, excluding `.gitkeep`); `ingested_ids(cfg) -> set[str]` (union of every page's `sources:`); `pending_sources(cfg) -> list[str]` (sorted `inbox_ids - ingested_ids`); `source_status(cfg) -> list[dict]` (`{id, ingested: bool}` for each inbox source).
- [ ] `cli.py`: `sources [--pending] [--json] [--wiki]` — list inbox sources with an `[ingested]`/`[pending]` marker (or only pending with `--pending`).
- [ ] `doctor.status`: add `pending_sources` (count); `status` command prints "Pending sources: N".
- [ ] Tests: a fresh `add-source`d file is pending; after a page references its id in `sources:`, it's ingested; `pending_sources` excludes ingested + `.gitkeep`; `sources` CLI marks each; `status` shows the pending count.

## Task P5.2: `quality.py` + `quality` command

**Files:** Create `src/llm_wiki/quality.py`; Modify `src/llm_wiki/cli.py`; Test `tests/test_quality.py`, `tests/test_cli_quality.py`.

- [ ] `quality.py`: `quality_score(fm, body) -> tuple[float, list[str]]` — weighted deterministic signals summing to 1.0: summary present (0.2), sources present (0.15), body ≥ ~30 words (0.2), confidence set (0.15), has links (`[[` in body or `related`) (0.15), tags present (0.15); returns `(round(score,2), missing_factors)`. `quality_report(cfg, limit=None) -> list[dict]` (`{slug, score, missing}` sorted by score ascending).
- [ ] `cli.py`: `quality [--limit N] [--json] [--wiki]` — list weakest pages with score + what they're missing.
- [ ] Tests: a bare page scores low and lists missing factors; a rich page (summary+sources+tags+links+confidence+body) scores high; `quality_report` orders weakest first; unparseable pages skipped.

## Task P5.3: `maintain` command + proactive SessionStart hook

**Files:** Modify `src/llm_wiki/hooks.py`, `src/llm_wiki/cli.py`; Test `tests/test_hooks.py`, `tests/test_cli_maintain.py`.

- [ ] `hooks.py`: add a `SessionStart` entry to `_DESIRED` (`llm-wiki hook session-start`); extend `run_hook` with `event == "session-start"`: find the wiki from the payload `cwd` (fallback cwd); if none → `(0, "")`; else build a short summary from `pending_sources` + `lifecycle.review` + `lint.run_lint` error count + `catalog.index_is_current`; return `(0, summary)` (empty string when nothing is notable, to avoid noise).
- [ ] `cli.py`: `maintain [--wiki]` — rebuild `index.md`, run `lint`, and print a consolidated report (lint errors/warnings, review-due, pending sources, weakest-quality count). Exit 0 (reporting), but note error count.
- [ ] Tests: `run_hook("session-start", payload-with-cwd)` returns a summary mentioning pending/review when present and `(0, "")` for a clean wiki; install_hooks now includes a SessionStart entry and uninstall removes it (the existing idempotency/round-trip tests still hold); `maintain` rebuilds the index and prints the report.

## Task P5.4: SCHEMA guidance + integration + review

**Files:** Modify `src/llm_wiki/templates/SCHEMA.md`; Test `tests/test_integration_phase5.py`.

- [ ] SCHEMA.md "Staying current" section: at session start (or when prompted by the hook), run `llm-wiki sources --pending` and `/wiki-ingest` each pending source; run `llm-wiki review` and refresh/`supersede` what it surfaces; the CLI never calls an LLM — you do the reading/writing.
- [ ] Integration test: init → `add-source` two files → `sources` shows both pending → `/`-style flow: `new-page` referencing one source → that one becomes ingested, the other still pending → `maintain` reports 1 pending + the lint/review summary → SessionStart hook summary mentions the pending source.
- [ ] Full suite green; `uv build` clean; `llm-wiki --help` lists `sources`/`quality`/`maintain`. Reinstall the global tool only if deps changed (they don't). Then dispatch the holistic review.

---

## After Phase 5
The full v1+v2 LLM-wiki vision (Phases 1–5) is complete. Possible follow-ons: shipped use-case templates (`--template`), the optional headless `--llm` driver (B-mode) for unattended cron, PyPI release.
