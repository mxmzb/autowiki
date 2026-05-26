# llm-wiki

Initialize and maintain [Karpathy-style LLM wikis](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
in any new or existing project. An agent maintains an interconnected set of markdown notes about
your sources; `llm-wiki` does the deterministic bookkeeping (scaffolding, indexing, linking, search,
lint) so the agent can focus on the reading and writing.

## Install (local dev)

```
uv tool install --editable .
```

Edits to the source take effect immediately, but the globally-installed tool has its own isolated
environment — after a **dependency change** (e.g. a new package), re-run
`uv tool install --editable . --reinstall` so the global `llm-wiki` picks it up.

## Quick start

```
llm-wiki init . --target claude      # scaffold wiki/ + CLAUDE.md managed block + slash commands
                                     #   --target generic for AGENTS.md; --root for a wiki at repo root
                                     #   --hooks to install opt-in Claude hygiene hooks
llm-wiki add-source notes.md         # vendor an existing file/URL into wiki/inbox/  → prints a source id
llm-wiki new-source "Meeting Notes"  # create a fresh inbox source (empty, or pipe content in)
llm-wiki new-page "Topic" --type concept --summary "…" --sources <id>
llm-wiki index                       # rebuild index.md from page frontmatter
llm-wiki log ingest "Topic"          # append to the chronological log.md
llm-wiki search "query"              # keyword search (hybrid keyword+semantic when embeddings are set up)
llm-wiki lint --fix                  # structural health check (orphans, broken links, stale, …)
llm-wiki graph neighbors <slug>      # explore the knowledge graph (also: path / hubs / stats / export)
llm-wiki supersede <old> <new>       # mark old superseded by new (kept, but dropped from the catalog)
llm-wiki review                      # surface pages that have decayed or are past review_by
llm-wiki sources --pending           # inbox sources not yet ingested into a page
llm-wiki quality                     # weakest pages (missing summaries, sources, links)
llm-wiki maintain                    # one-shot pass: rebuild index + lint/review/pending/quality report
llm-wiki status                      # page counts, status/tier breakdown, review-due, lint summary
llm-wiki doctor                      # health/setup check
llm-wiki upgrade                     # refresh schema/commands/block to the installed version
```

With `--hooks`, a SessionStart hook greets each Claude session with what needs attention (pending
sources, pages due for review, lint errors) so the in-session agent can act on it.

**Semantic search (optional):** `pip install 'llm-wiki[embeddings]'`, then `llm-wiki embed` to build a
local vector index — `search` then fuses keyword + semantic results, and `llm-wiki similar <slug>` finds
near-duplicate pages. Without the extra, search stays keyword-only.

Commands resolve the wiki from the current directory (walking up, and into a `wiki/` subdir), or
pass `--wiki <path>`.

## Layout

```
wiki/
├── inbox/        raw human-curated sources (agent read-only; add via `add-source`)
├── pages/        agent-owned markdown pages (entity | concept | source-summary | note)
├── index.md      generated catalog
├── log.md        append-only chronological ledger
├── SCHEMA.md     the maintainer playbook (edit to customize page types, rules, stale threshold)
└── .llm-wiki.toml
```

`index.md` and `log.md` are generated — let `llm-wiki` manage them. `inbox/` is read-only to the agent.

## Status

All five phases are complete: the core wiki + CLI, the knowledge graph, hybrid (keyword + semantic)
search, the memory lifecycle (confidence/decay with evergreen pages, supersession, `review`), and
automation/quality (source-ingestion tracking, `quality`, `maintain`, the proactive SessionStart hook).
The CLI is fully deterministic — the in-session agent does all semantic work. See
`docs/superpowers/specs/` and `docs/superpowers/plans/` for the design. Possible follow-ons: shipped
`--template` use-case templates, an optional headless `--llm` driver for unattended cron, and a PyPI release.
