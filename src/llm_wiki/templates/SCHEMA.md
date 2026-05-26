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
Typed edges: `relations: [{predicate: <verb>, target: <slug>}]` — e.g. `{predicate: uses, target: pytorch}`.
These (with `[[links]]` and `related`) form the knowledge graph (see below).
Reserved (leave defaults unless you know them): `status`, `confidence`, `review_by`,
`supersedes`, `superseded_by`, `contradicts`, `tier`, `entities`.

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
2. Surface connections search misses: `llm-wiki graph neighbors <slug>` and `llm-wiki graph path <a> <b>`.
3. Synthesize an answer with `[[links]]` to your sources.
4. If the answer is reusable, `llm-wiki new-page --type note`, write it, then `llm-wiki index` and `llm-wiki log query "<question>"`.

### Lint
1. `llm-wiki lint --json`; read the issues.
2. Fix broken links, orphans, missing summaries, and stale pages. Re-run `llm-wiki lint` until clean.

## Knowledge graph
Pages are nodes; edges come from `[[wiki-links]]`, the `related`/`supersedes`/`contradicts` lists, and
typed `relations`. The graph is computed on demand — query it with:
- `llm-wiki graph neighbors <slug> [--depth N] [--predicate P]` — connected pages.
- `llm-wiki graph path <a> <b>` — how two pages connect.
- `llm-wiki graph hubs` — the most-connected (most important) pages.
- `llm-wiki graph stats` / `llm-wiki graph export --format dot|json`.
Strengthen the graph during ingest by adding `relations` entries and `[[links]]` between related pages.

## Semantic search
If the embeddings extra is installed (`pip install 'llm-wiki[embeddings]'`), run `llm-wiki embed` to
(re)build the vector index; then `llm-wiki search` automatically fuses keyword + semantic results.
Use `llm-wiki similar <slug>` to find near-duplicate pages **before** creating a new one. Without the
extra, search is keyword-only — everything still works.

## Memory lifecycle
- Set `confidence` (0–1) on facts — well-established ones decay slower.
- Mark timeless pages `evergreen: true` (or `llm-wiki new-page --evergreen`): they never decay or go stale.
- Use `tier` to reflect consolidation: `working` (raw notes) → `episodic` (session summaries) →
  `semantic` (established facts) → `procedural` (workflows). Lower tiers decay faster.
- **Supersede, don't delete:** `llm-wiki supersede <old> <new>` marks the old page superseded — it
  drops out of `index.md` but stays searchable and points to its replacement.
- Run `llm-wiki review` to surface pages that have decayed or are past their `review_by` date.

## Staying current
At the start of a session (the SessionStart hook surfaces what's pending), keep the wiki fresh:
- `llm-wiki sources --pending` lists inbox sources not yet ingested — run the **Ingest a source**
  workflow on each.
- `llm-wiki review` surfaces decayed/overdue pages — refresh or `supersede` them.
- `llm-wiki maintain` rebuilds the index and reports lint/review/pending/quality in one pass.
- `llm-wiki quality` shows the weakest pages (missing summaries, sources, or links).

The CLI never calls an LLM — these commands just tell you what needs attention; you do the reading and writing.

## Customizing your wiki
This file is yours to edit. To adapt the wiki to your use case:
- **Add a page type:** describe it here under "Page types", add it to `[wiki].extra_types` in
  `.llm-wiki.toml`, and use `llm-wiki new-page --type <yourtype>`.
- **Change the stale threshold:** set `stale_days` in `.llm-wiki.toml`.
- **Change conventions:** edit the rules above; the CLI enforces structure, this file guides judgement.
