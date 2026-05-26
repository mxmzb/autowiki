# LLM Wiki Phase 4 — Memory Lifecycle & Tiers Implementation Plan

> **Execution note:** Inline TDD by the controller, commit per task, single holistic review at the end.

**Goal:** Give the wiki a memory lifecycle — confidence- and tier-weighted decay (with **evergreen** pages exempt), supersession bookkeeping, and a `review` surface for what needs attention — without losing any content. Archived (superseded/deprecated) pages drop out of the `index.md` catalog but stay searchable.

**Design (approved). Approach A: the agent makes the judgments (confidence, what supersedes what, what's evergreen, when to consolidate); the CLI does the deterministic math + bookkeeping. No LLM in the CLI.**
- Decay is **conditional**: `evergreen: true` pages never decay; others decay (Ebbinghaus) by age-since-`updated`, with rate set by `tier` (working/episodic fast → semantic/procedural slow) and `confidence`.
- `index.md` excludes `superseded`/`deprecated` pages (count noted); **search is unchanged** (still finds everything).

**Tech Stack:** Python ≥3.11 (stdlib `math`/`datetime`), Typer, pytest.

---

## Task P4.1: `evergreen` field + `lifecycle.py`

**Files:** Modify `src/llm_wiki/frontmatter.py` (add `evergreen`); Create `src/llm_wiki/lifecycle.py`; Test `tests/test_frontmatter.py`, `tests/test_lifecycle.py`.

- [ ] `frontmatter.py`: add `evergreen: bool = False` to `PageFrontmatter`; in `_coerce_shapes`, coerce a present `evergreen` to `bool`. (No validate change.)
- [ ] `lifecycle.py`:
  - `_TIER_STRENGTH = {"working": 14, "episodic": 60, "semantic": 365, "procedural": 730}` (default 365).
  - `retention(fm, now=None) -> float`: `1.0` if `fm.evergreen`; else `exp(-age_days / strength)` where `age_days` = days since `updated` (bad/empty date → 0), `strength = tier_strength * (0.5 + confidence)` with `confidence` defaulting to 0.5 when unset/non-numeric. Clamped to (0, 1].
  - `review(cfg, threshold=0.5) -> list[dict]`: for each parseable, **non-evergreen** page, collect `reasons` = `review_by passed` (review_by ≤ today) / `decayed` (retention < threshold) / `low confidence` (confidence < 0.3); include pages with ≥1 reason as `{slug, title, retention, reasons}`, sorted by retention ascending.
  - `supersede(cfg, old_slug, new_slug) -> None`: both pages must exist (else `FileNotFoundError`); append `new` to `old.superseded_by`, set `old.status = "superseded"`, append `old` to `new.supersedes`, bump both `updated`; write both (via `frontmatter.dump`, preserving bodies).
- [ ] Tests: evergreen → retention 1.0 regardless of age; an old working-tier page decays below an old semantic-tier page; higher confidence decays slower; `review` lists decayed/overdue pages and **omits evergreen**; `supersede` wires both sides + sets status + is idempotent on re-run.

## Task P4.2: index exclusion + lint lifecycle checks

**Files:** Modify `src/llm_wiki/catalog.py`, `src/llm_wiki/lint.py`; Test `tests/test_catalog.py`, `tests/test_lint.py`.

- [ ] `catalog.build_index`: skip pages whose `status` is `superseded`/`deprecated`; if any were skipped, append a trailing line `_<n> archived page(s) hidden._`. (Empty/active wikis unchanged.)
- [ ] `lint.run_lint`: (a) exempt `evergreen` pages from the existing `stale` check; (b) **supersession consistency** (error): if A lists B in `supersedes` but B's `superseded_by` lacks A (or vice versa) → `supersession_inconsistent`; (c) **archived-but-active** (warning): a page whose `superseded_by` is non-empty but `status != "superseded"` → `archived_status`.
- [ ] Tests: a superseded page is absent from `build_index` and the hidden-count note appears; an evergreen page past `review_by` is NOT flagged stale; one-sided supersession flagged; `superseded_by` set with status active flagged.

## Task P4.3: CLI — supersede / review / new-page options / status

**Files:** Modify `src/llm_wiki/pages.py` (new_page options), `src/llm_wiki/cli.py`, `src/llm_wiki/doctor.py` (status); Test `tests/test_pages.py`, `tests/test_cli_lifecycle.py`, `tests/test_doctor.py`.

- [ ] `pages.new_page`: add `tier="semantic"`, `confidence: float | None = None`, `evergreen: bool = False` params, written into frontmatter.
- [ ] `cli.py`: `new-page` gains `--tier`, `--confidence`, `--evergreen`. New commands: `supersede <old> <new>` (calls lifecycle.supersede; FileNotFoundError → exit 1); `review [--threshold] [--json] [--wiki]` (prints ranked pages + reasons; empty → "Nothing needs review.").
- [ ] `doctor.status`: add `by_status`, `by_tier`, and `review_due` (len of `lifecycle.review(cfg)`); `status` command prints them.
- [ ] Tests: `new-page --tier procedural --evergreen --confidence 0.9` persists those fields; `supersede A B` makes B supersede A and marks A superseded (exit 0); `supersede` with a missing page exits 1; `review` lists an overdue page; `status` shows tier/status breakdown + review-due count.

## Task P4.4: SCHEMA guidance + integration + review

**Files:** Modify `src/llm_wiki/templates/SCHEMA.md`; Test `tests/test_integration_phase4.py`.

- [ ] SCHEMA.md: a "Memory lifecycle" section — set `confidence` on facts; mark timeless pages `evergreen`; use `llm-wiki supersede <old> <new>` instead of deleting; consolidate `working → episodic → semantic → procedural` via the `tier` field; run `llm-wiki review` to find what needs attention.
- [ ] Integration test: init → pages (one evergreen, one stale-dated) → `review` lists the stale one and omits evergreen → `supersede` old→new → old leaves `index.md` but is still found by `search` → `lint` clean of errors → `doctor`/`status` show the lifecycle counts.
- [ ] Full suite green; `uv build` clean; `llm-wiki --help` lists `supersede`/`review`. Then dispatch the holistic review.

---

## After Phase 4
Phase 5 (automation/quality — proactive hooks, scheduled decay/review, semantic contradiction resolution) is the final phase.
