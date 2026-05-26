# LLM Wiki Phase 3 — Hybrid Search Implementation Plan

> **Execution note:** Inline TDD by the controller, commit per task, single holistic review at the end. Tests inject a deterministic **fake embedding backend** — no model downloads, fully offline/fast.

**Goal:** Add a local-first vector retrieval leg and fuse it with BM25 via reciprocal rank fusion, so `search` finds semantically-related pages keyword search misses. New verbs `embed` (build/update the vector index) and `similar <slug>`. Vector support is an **optional extra**; without it, everything degrades gracefully to BM25.

**Design (approved):**
- Vector leg is `pip install llm-wiki[embeddings]` (lightweight local ONNX model, no torch). Not installed → `search` stays BM25(+graph), `doctor` reports it. Optional API backend via config.
- Embedding backend is **pluggable behind an interface**; tests inject a fast deterministic fake (feature-hashed bag-of-words) so the suite needs no model and stays offline.
- Vectors + per-page content hashes + model name stored in a flat file under gitignored `.index/`; brute-force cosine (instant at wiki scale); **incremental** (`embed` only re-encodes changed pages). Markdown stays source of truth (rebuildable).
- Hybrid `search` = RRF over BM25 ranks + vector ranks; `similar <slug>` = vector nearest pages.

**Tech Stack:** Python ≥3.11; `numpy` + `fastembed` in the `embeddings` extra (lazy-imported so core works without them); Typer; pytest.

---

## Task P3.1: `embeddings.py` — backend interface + local backend + fake injection

**Files:** Create `src/llm_wiki/embeddings.py`; Modify `pyproject.toml`; Test `tests/test_embeddings.py`; Modify `tests/conftest.py` (FakeBackend + fixture).

- [ ] `pyproject.toml`: add `[project.optional-dependencies] embeddings = ["fastembed>=0.3", "numpy>=1.24"]`; add `numpy>=1.24` to `dev` (tests need it). Core deps unchanged.
- [ ] `embeddings.py`: `EmbeddingBackend` Protocol (`name: str`, `dim: int`, `embed(texts: list[str]) -> list[list[float]]`); `available() -> bool` (can a backend be constructed?); `get_backend(cfg) -> EmbeddingBackend | None` honoring a module-level test override, else `cfg.embedding_provider` (`local` → `FastEmbedBackend`, `openai`/`voyage` → stub raising NotImplementedError for now, returns None if the lib is missing); `set_test_backend(b)` / `clear_test_backend()`. `FastEmbedBackend` lazy-imports `fastembed` in `__init__` (so importing the module never requires it).
- [ ] `conftest.py`: `FakeBackend` (dim 64, feature-hashed bag-of-words, pure-Python, deterministic — more shared words ⇒ higher cosine); `fake_embeddings` fixture that `set_test_backend(FakeBackend())` and clears on teardown.
- [ ] Tests: `available()`/`get_backend` return the fake when overridden; FakeBackend gives identical vectors for identical text and higher overlap ⇒ closer (sanity); importing `embeddings` works without fastembed/numpy installed at import time.

## Task P3.2: `vectorindex.py` — build/update/load/query/similar

**Files:** Create `src/llm_wiki/vectorindex.py`; Test `tests/test_vectorindex.py`.

- [ ] Storage in `cfg.index_dir`: `vectors.npy` (float32 `(N, dim)`) + `embeddings.json` (`{model, dim, slugs: [...], hashes: {slug: sha256}}`). numpy lazy-imported.
- [ ] `page_text(fm, body) -> str` and `content_hash(text) -> str` (sha256 of the page's title+summary+tags+body).
- [ ] `build_or_update(cfg, backend) -> dict` (counts: added/updated/removed/unchanged): load existing; if stored model != backend.name → full rebuild; else re-embed only pages whose hash changed, drop removed pages, keep unchanged; write store. Returns summary.
- [ ] `load(cfg) -> (slugs, matrix) | None` (None if no store).
- [ ] `query_vector(cfg, vector, limit) -> list[tuple[slug, score]]` (cosine, desc). `similar(cfg, slug, backend, limit) -> list[tuple[slug, score]]` (uses the slug's stored vector; excludes self).
- [ ] Tests (with `fake_embeddings`): build over a few pages writes the store; re-running unchanged ⇒ 0 updated; editing one page ⇒ 1 updated; deleting a page ⇒ removed; `similar` ranks the most word-overlapping page first; `query_vector` returns sorted hits.

## Task P3.3: hybrid fusion in `search.py`

**Files:** Modify `src/llm_wiki/search.py`; Test `tests/test_search.py`.

- [ ] Refactor existing BM25 logic into a helper returning ranked `Hit`s. Add `_rrf(rankings: list[list[str]], k=60) -> dict[str,float]`.
- [ ] `search(cfg, query, type=None, tag=None, limit=10, hybrid=None)`: compute BM25 ranking; if a backend is available AND a vector store exists (and `hybrid` not False), also compute the vector ranking (embed query → `query_vector`), fuse slugs via RRF, then materialize `Hit`s (respecting type/tag filters) in fused order; else BM25 only. `hybrid=True` with no backend/store → BM25 (caller may warn).
- [ ] Tests (with `fake_embeddings` + a built index): a page that shares few keywords but high word-overlap still surfaces via the vector leg; hybrid result order reflects fusion; with no backend, `search` behaves exactly as before (BM25).

## Task P3.4: CLI `embed` / `similar` / `search --hybrid` + doctor + guidance

**Files:** Modify `src/llm_wiki/cli.py`, `src/llm_wiki/doctor.py`, `src/llm_wiki/templates/SCHEMA.md`; Test `tests/test_cli_embeddings.py`.

- [ ] `embed [--wiki]`: build/update the index; if no backend → message "install llm-wiki[embeddings]" + exit 1. Print the summary counts.
- [ ] `similar <slug> [--limit] [--json] [--wiki]`: nearest pages; no backend/store → exit 1 with guidance; missing slug → exit 1.
- [ ] `search` gains `--hybrid/--no-hybrid` (default auto); when `--hybrid` requested but unavailable, print a stderr note and fall back.
- [ ] `doctor`: report embedding backend availability (available vs "not installed — `pip install llm-wiki[embeddings]`") and whether a vector index exists/and if it's stale vs current page hashes.
- [ ] SCHEMA.md: short "Semantic search" note (`llm-wiki embed` to build; `search` is hybrid when available; `similar` to find near-duplicates before creating a page).
- [ ] Tests (CliRunner + `fake_embeddings`): `embed` builds + reports counts; `similar <slug>` returns hits; `embed` with backend unavailable exits 1; `search --hybrid` works with a built index.

## Task P3.5: integration + review

**Files:** Test `tests/test_integration_phase3.py`.

- [ ] Integration (fake backend): init → pages → `embed` → `search` (hybrid finds a low-keyword/high-meaning match) → `similar` → edit a page → `embed` re-encodes only it → `doctor` reports index present.
- [ ] Full suite green; `uv build` clean; `.index/` gitignored (no vectors tracked). Attempt a real-backend smoke (`uv pip install '.[embeddings]'` then `llm-wiki embed`/`similar`) if feasible; otherwise document that the real backend is wired + fake-tested. Then dispatch the holistic review.

---

## After Phase 3
Phase 4 (memory lifecycle/decay + consolidation tiers) and Phase 5 (automation/quality) remain.
