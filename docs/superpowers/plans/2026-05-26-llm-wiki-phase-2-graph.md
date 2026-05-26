# LLM Wiki Phase 2 — Knowledge Graph Implementation Plan

> **Execution note:** Inline TDD by the controller, commit per task, single holistic review at the end (same as Milestone B/C).

**Goal:** Add a deterministic knowledge-graph layer over the wiki — `graph` queries (neighbors, path, hubs, stats, export) computed on demand from page frontmatter + wiki-links — so the connections between pages become queryable, surfacing relationships keyword search misses.

**Design (approved):**
- **Node = page** (id = slug; attrs `type`, `title`).
- **Edges** from existing page content, no new authoring burden: inline `[[wikilinks]]` (predicate `links`); relational frontmatter `related`/`supersedes`/`superseded_by`/`contradicts` (predicate = the field name); and the Phase-1 `relations: [{predicate, target}]` seam, now consumed (predicate-typed edges). Edges to unknown targets are skipped (lint reports them as broken links).
- **Computed on demand** with `networkx` (new dependency) from the markdown — no separate stored graph; markdown stays the source of truth.
- Still fully Approach A: the CLI builds/queries deterministically; the agent's only job is to write good links/relations (guided by SCHEMA.md).

**Tech Stack:** Python ≥3.11, `networkx` (new dep), Typer, `pytest`.

---

## Task P2.1: `graph.py` — build_graph + queries

**Files:** Create `src/llm_wiki/graph.py`; Modify `pyproject.toml` (add `networkx>=3`); Test `tests/test_graph.py`.

- [ ] Add `networkx>=3` to `[project].dependencies`; `uv lock`/sync.
- [ ] `build_graph(cfg) -> networkx.DiGraph`: add a node per page (`type`, `title`); then add edges from `[[wikilinks]]` in the body, from `related`/`supersedes`/`superseded_by`/`contradicts`, and from `relations` dict entries (`{predicate, target}`). **Only add an edge when the target is an existing node** (skip phantom/broken targets). Tolerant of unparseable pages (skip).
- [ ] `neighbors(g, slug, depth=1, predicate=None) -> list[dict]`: undirected BFS from `slug` up to `depth`, excluding self; each result `{slug, title, distance}`, sorted by `(distance, slug)`. If `predicate` given, only traverse edges with that predicate. Raise `KeyError` if `slug` not a node.
- [ ] `path(g, a, b) -> list[str] | None`: shortest undirected path (list of slugs) or `None` if disconnected / missing node.
- [ ] `hubs(g, limit=10) -> list[dict]`: nodes by total degree (in+out) desc; `{slug, title, degree}`.
- [ ] `stats(g) -> dict`: `{nodes, edges, by_type: {type: n}, isolated: n}`.
- [ ] `export(g, fmt) -> str`: `"json"` → `json.dumps(networkx.node_link_data(g))`; `"dot"` → a hand-built Graphviz `digraph` (no extra dep) with node labels = titles and edge labels = predicate.
- [ ] Tests: nodes per page; edges from links/related/relations; edge to unknown target skipped; neighbors depth 1 & 2 and predicate filter; path connected → slug list, disconnected → None; hubs orders most-connected first; stats counts; export json has nodes/links, dot has `digraph`.

## Task P2.2: lint + frontmatter for `relations`

**Files:** Modify `src/llm_wiki/lint.py`, `src/llm_wiki/frontmatter.py`; Test `tests/test_lint.py`.

- [ ] `frontmatter._coerce_shapes`: for `relations`/`entities` list entries, drop non-dict items; for dict items, coerce a present `target`/`predicate` to `str`. (Keeps build_graph/lint safe on hand-edited relations.)
- [ ] `lint.run_lint`: extend the broken-link check to include `relations` dict-entry targets (unresolved `relations[].target` → `broken_link` error).
- [ ] Tests: a page with `relations: [{predicate: uses, target: ghost}]` (no `ghost` page) yields `broken_link`; a resolving relations target does not; a malformed relations entry (a bare string) doesn't crash lint.

## Task P2.3: `graph` CLI command

**Files:** Modify `src/llm_wiki/cli.py`; Test `tests/test_cli_graph.py`.

- [ ] Add a `graph` sub-app (`typer.Typer()`, `app.add_typer(..., name="graph")`) with: `neighbors <slug> [--depth N] [--predicate P] [--json] [--wiki]`, `path <a> <b> [--json] [--wiki]`, `hubs [--limit N] [--json] [--wiki]`, `stats [--json] [--wiki]`, `export [--format dot|json] [--wiki]`. Each resolves the wiki via `_resolve_cfg`, builds the graph, runs the query. `neighbors`/`path` on a missing slug → clear message + exit 1. Text output is readable; `--json` emits structured data.
- [ ] Tests (CliRunner): build a small wiki with links/relations; `graph neighbors`, `graph path`, `graph hubs --json`, `graph stats`, `graph export --format dot` all exit 0 and produce expected content; `graph neighbors missing` exits 1.

## Task P2.4: agent guidance + integration + review

**Files:** Modify `src/llm_wiki/templates/SCHEMA.md`, `src/llm_wiki/templates/command_wiki-query.md`; Test `tests/test_integration_phase2.py`.

- [ ] SCHEMA.md: add a short "Knowledge graph" note (edges come from links + `relations`; use `llm-wiki graph neighbors/path` during query to surface connections) and document the `relations: [{predicate, target}]` field for typed edges. Update `/wiki-query` to suggest a `graph neighbors`/`graph path` step.
- [ ] Integration test: init → pages with `[[links]]` + `relations` → `graph neighbors`/`path`/`hubs` reflect the structure → `lint` flags a broken `relations` target.
- [ ] Run full suite; confirm `uv build` clean and `llm-wiki graph --help` lists the subcommands. Then dispatch the holistic review.

---

## After Phase 2
Phase 3 (hybrid/vector search) builds on this graph + BM25. Then Phase 4 (memory lifecycle) and Phase 5 (automation/quality).
