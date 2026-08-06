# LLM Wiki — Maintainer Schema

This file tells you (the agent) how to maintain this wiki. It is the operating manual.
All structural bookkeeping is done by the `autowiki` CLI; you do the reading and writing.

## Layers
- `inbox/` — raw, human-curated sources. **Read-only.** Add only via `autowiki add-source`.
- `pages/` — the wiki you own: `entity`, `concept`, `source-summary`, and `note` pages.
- `index.md` / `log.md` — **generated**. Never hand-edit; use `autowiki index` / `autowiki log`.

## Invariants
1. Create pages with `autowiki new-page` so frontmatter is correct. Never hand-write a new page file.
2. Before creating a page, run `autowiki search "<topic>"` — prefer updating an existing page over duplicating.
3. After any change to `pages/`, run `autowiki index` then `autowiki lint` and fix what it reports.
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
1. `autowiki add-source <path|url>` → note the returned source id.
2. Read the source. Identify the entities, concepts, and key claims.
3. Discuss findings with the user (skip if running non-interactively).
4. `autowiki new-page --type source-summary --title "..." --sources <id>` and write the summary.
5. For each entity/concept: `autowiki search` first; update the existing page or `autowiki new-page`. Add `[[links]]`.
6. `autowiki index` → `autowiki log ingest "<title>"` → `autowiki lint` (fix issues).

### Answer a query
1. `autowiki search "<question>"`; read the top pages.
2. Surface connections search misses: `autowiki graph neighbors <slug>` and `autowiki graph path <a> <b>`.
3. Synthesize an answer with `[[links]]` to your sources.
4. If the answer is reusable, `autowiki new-page --type note`, write it, then `autowiki index` and `autowiki log query "<question>"`.

### Lint
1. `autowiki lint --json`; read the issues.
2. Fix broken links, orphans, missing summaries, and stale pages. Re-run `autowiki lint` until clean.

## Knowledge graph
Pages are nodes; edges come from `[[wiki-links]]`, the `related`/`supersedes`/`contradicts` lists, and
typed `relations`. The graph is computed on demand — query it with:
- `autowiki graph neighbors <slug> [--depth N] [--predicate P]` — connected pages.
- `autowiki graph path <a> <b>` — how two pages connect.
- `autowiki graph hubs` — the most-connected (most important) pages.
- `autowiki graph stats` / `autowiki graph export --format dot|json`.
Strengthen the graph during ingest by adding `relations` entries and `[[links]]` between related pages.

## Semantic search
If the embeddings extra is installed (`pip install 'autowiki[embeddings]'`), run `autowiki embed` to
(re)build the vector index; then `autowiki search` automatically fuses keyword + semantic results.
Use `autowiki similar <slug>` to find near-duplicate pages **before** creating a new one. Without the
extra, search is keyword-only — everything still works.

## Memory lifecycle
- Change frontmatter fields with `autowiki set <slug>` (e.g. `--confidence 0.8`, `--tier semantic`,
  `--status`, `--review-by`, `--add-source`, `--add-related`, `--add-tag`) — it validates and bumps
  `updated` for you. Prefer it over hand-editing YAML.
- Set `confidence` (0–1) on facts — well-established ones decay slower.
- Mark timeless pages `evergreen: true` (or `autowiki new-page --evergreen`): they never decay or go stale.
- Use `tier` to reflect consolidation: `working` (raw notes) → `episodic` (session summaries) →
  `semantic` (established facts) → `procedural` (workflows). Lower tiers decay faster.
- **Supersede, don't delete:** `autowiki supersede <old> <new>` marks the old page superseded — it
  drops out of `index.md` but stays searchable and points to its replacement.
- Run `autowiki review` to surface pages that have decayed or are past their `review_by` date.

## Staying current
At the start of a session (the SessionStart hook surfaces what's pending), keep the wiki fresh:
- `autowiki sources --pending` lists inbox sources not yet ingested — run the **Ingest a source**
  workflow on each.
- `autowiki review` surfaces decayed/overdue pages — refresh or `supersede` them.
- `autowiki maintain` rebuilds the index and reports lint/review/pending/quality in one pass.
- `autowiki quality` shows the weakest pages (missing summaries, sources, or links).

The CLI never calls an LLM — these commands just tell you what needs attention; you do the reading and writing.

## Customizing your wiki
This file is yours to edit. To adapt the wiki to your use case:
- **Add a page type:** describe it here under "Page types", add it to `[wiki].extra_types` in
  `.autowiki.toml`, and use `autowiki new-page --type <yourtype>`.
- **Change the stale threshold:** set `stale_days` in `.autowiki.toml`.
- **Change conventions:** edit the rules above; the CLI enforces structure, this file guides judgement.
