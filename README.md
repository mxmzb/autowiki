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
llm-wiki add-source notes.md         # vendor a source into wiki/inbox/  → prints a source id
llm-wiki new-page "Topic" --type concept --summary "…" --sources <id>
llm-wiki index                       # rebuild index.md from page frontmatter
llm-wiki log ingest "Topic"          # append to the chronological log.md
llm-wiki search "query"              # BM25 over your pages
llm-wiki lint --fix                  # structural health check (orphans, broken links, stale, …)
llm-wiki status                      # page counts, last log entry, lint summary
llm-wiki doctor                      # health/setup check
llm-wiki upgrade                     # refresh schema/commands/block to the installed version
```

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

Phase 1 (the core wiki + CLI) is complete. See `docs/superpowers/specs/` and `docs/superpowers/plans/`
for the design and the phased roadmap (Phase 2 knowledge graph, Phase 3 hybrid/vector search,
Phase 4 memory lifecycle, Phase 5 automation/quality).
