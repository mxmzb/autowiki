# LLM Wiki — Phase 1 Design

**Date:** 2026-05-25
**Status:** Approved (pending written-spec review)
**Repo:** `init-llm-wiki`

---

## 1. Context & vision

This project implements [Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
and its [v2 extension](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2)
as a tool you can drop into new or existing projects.

**Karpathy's pattern (v1)** is a three-layer knowledge base maintained by an agent:

- **Raw sources** — immutable, human-curated inputs; the agent reads but never edits them.
- **The wiki** — interconnected markdown the agent owns (summaries, entity/concept pages,
  a generated `index.md` catalog, an append-only `log.md` ledger).
- **The schema** — a `CLAUDE.md`/`AGENTS.md` that tells the agent how to behave as wiki maintainer.

Three operations: **ingest** (read source → summarize → cross-link → log), **query**
(search → synthesize → optionally crystallize a new page), **lint** (find contradictions,
stale claims, orphans). The guiding insight: *the hard part of a knowledge base is the
bookkeeping, not the thinking* — so the agent does the thinking and the tooling does the bookkeeping.

**The v2 extension** layers on memory lifecycle (confidence/decay/supersession), consolidation
tiers (working → episodic → semantic → procedural), a typed knowledge graph, hybrid search
(BM25 + vector + graph with rank fusion), and event-driven automation/quality hooks.

### Product shape (settled)

- A **globally-installed, versioned Python CLI** (`llm-wiki`, managed with `uv`, PyPI later)
  holds the canonical scripts, templates, and logic.
- `llm-wiki init` drops a **thin per-project scaffold** that references the global tool, so
  upgrading the package upgrades every wiki's behavior — no stale copied scripts.
- The agent (Claude or any other) reads the scaffolded schema and does the semantic work.

### Phasing (the full v1 + v2 ambition, built in shippable layers)

Each phase is its own spec → plan → build cycle. **This document specs Phase 1 only.**

1. **Phase 1 — Core wiki + CLI foundation (v1, built v2-ready).** ← this spec
2. **Phase 2 — Knowledge graph layer.** Typed entity/relationship extraction from frontmatter +
   links (`networkx`), graph-traversal queries.
3. **Phase 3 — Hybrid search.** Local-first vector embeddings + BM25 + graph traversal fused via
   reciprocal rank fusion.
4. **Phase 4 — Memory lifecycle + consolidation tiers.** Confidence scoring, supersession,
   Ebbinghaus decay, working/episodic/semantic/procedural consolidation.
5. **Phase 5 — Automation, quality, self-healing.** Proactive/scheduled hooks, quality scoring,
   semantic contradiction detection + resolution.

### Architecture decision (Approach A)

**Thin, LLM-free CLI for deterministic bookkeeping; the agent does the semantics.**

- The CLI never calls an LLM *to generate or judge wiki prose*. (Computing embeddings in Phase 3 is
  numeric encoding, not prose generation, so that stays in the CLI.)
- Semantic operations (ingest/query) are **agent workflows** defined in `SCHEMA.md`, exposed on the
  Claude target as thin slash-command wrappers that call the same CLI verbs.
- Everything funnels through the CLI verbs, so behavior is identical across agents.
- A clean seam is kept around the single semantic step of ingest ("turn this source content into a
  structured page") so an **optional headless `--llm` driver (B-mode)** can be added later — reusing
  the same plumbing — without rework. (Deferred; relevant to Phase 5 automation.)

---

## 2. On-disk layout

```
project-root/
├── CLAUDE.md  (or AGENTS.md)        # existing or created; init injects a managed block
├── .gitignore                       # we add wiki/.index/ if a root .gitignore exists
├── wiki/
│   ├── inbox/                       # raw human-curated sources, agent read-only   [.gitkeep]
│   ├── pages/                       # agent-owned wiki markdown pages              [.gitkeep]
│   ├── index.md                     # GENERATED catalog of all pages
│   ├── log.md                       # append-only chronological ledger
│   ├── SCHEMA.md                    # full maintainer playbook + customization guide
│   ├── .llm-wiki.toml               # config: schema_version, target, embedding settings, paths
│   ├── .gitignore                   # ignores .index/
│   └── .index/                      # derived search/vector data, rebuildable (Phase 3)
└── .claude/
    ├── commands/                    # Claude target only
    │   ├── wiki-ingest.md
    │   ├── wiki-query.md
    │   └── wiki-lint.md
    └── settings.json                # hooks added here only if --hooks (opt-in)
```

- `inbox/` keeps Karpathy's **permanent, human-curated, agent-read-only** source store — just a
  friendlier name than `sources/`. It is not a staging area that gets emptied.
- `.index/` is **derived data** (gitignored, always rebuildable). Markdown is the single source of truth.
- `--root` places everything at repo root instead of under `wiki/` (for dedicated wiki repos).
- `.llm-wiki.toml` **marks the wiki root** for command auto-discovery (walk-up search).

### What `init` writes

- The `wiki/` tree (`inbox/`, `pages/` seeded with `.gitkeep`; `.index/` reserved + gitignored).
- `index.md` — empty seeded catalog. `log.md` — seeded `## [YYYY-MM-DD] init | wiki initialized`.
- `SCHEMA.md` — maintainer playbook + "Customizing your wiki" section.
- `.llm-wiki.toml` — `schema_version`, `target`, `embedding.provider = "local"` (default), path overrides.
- `wiki/.gitignore` — ignores `.index/`.
- A **managed block** in the root `CLAUDE.md`/`AGENTS.md` (created if absent), between markers, idempotent.
- Claude target only: `.claude/commands/wiki-{ingest,query,lint}.md`; and, if `--hooks`, hook entries in
  `.claude/settings.json`.

### Targets, idempotency, existing projects

- `--target claude` (managed block + slash commands [+ hooks if `--hooks`]) or `--target generic`
  (AGENTS.md, no slash commands/hooks). Unspecified → detect (`.claude/`, existing `CLAUDE.md`/`AGENTS.md`),
  fall back to asking.
- Re-running `init` updates **only** the managed block in place and warns if `wiki/` already exists
  (directing to `upgrade`). Managed-block edits never clobber surrounding user content.
- `upgrade` refreshes `SCHEMA.md`, templates, slash commands, managed block, and (if installed) hooks to
  the installed `schema_version` and applies safe frontmatter migrations — **without touching** `inbox/`,
  `pages/`, `index.md`, or `log.md` content.

---

## 3. Page frontmatter schema & page types

Phase 1 **defines and validates the full schema** (every page is forward-compatible) but only **acts on**
the v1 subset. Later phases turn on behavior for the rest — no migration needed.

### Frontmatter (YAML) on every page in `wiki/pages/`

| Field | Phase 1 behavior | Purpose / later use |
|---|---|---|
| `title` | **required**, used by `index` | human title |
| `type` | **required**, validated enum | page type (below) |
| `created` / `updated` | **required**, set by `new-page`/edits | also feed stale checks |
| `summary` | used by `index` (one-line catalog entry) | the catalog line |
| `slug` | derived from filename, uniqueness enforced | stable id for links |
| `tags` | indexed, lint-validated (default `[]`) | grouping |
| `aliases` | lint-validated (default `[]`) | alt names → link/entity matching (P2) |
| `sources` | lint checks they exist in `inbox/` (default `[]`) | provenance |
| `related` | lint checks targets resolve (default `[]`) | explicit cross-refs → graph (P2) |
| `status` | defaulted `active`, shape-validated | `active\|draft\|deprecated\|superseded` (P4/5) |
| `confidence` | defaulted unset, shape-validated | lifecycle scoring (P4) |
| `review_by` | shape-validated; **lint already flags stale** | freshness/decay (P4) |
| `supersedes` / `superseded_by` | shape-validated (default `[]`) | supersession tracking (P4) |
| `contradicts` | shape-validated (default `[]`) | structural contradiction hooks (P5) |
| `tier` | defaulted `semantic`, shape-validated | consolidation tier (P4) |
| `entities` / `relations` | shape-validated (default `[]`) | typed graph hints, e.g. `{predicate, target}` (P2) |

`content_hash` is **not** in frontmatter (editing it would change the content it hashes) — it lives in
`.index/` for incremental embedding (Phase 3).

### Page types (Phase 1 enum; defined in `SCHEMA.md`; user-extensible)

- `source-summary` — a summary of one ingested source (carries its `sources:`).
- `entity` — a person/project/library/org/place (the "nouns").
- `concept` — an idea/topic/theme.
- `note` — a crystallized query answer or cross-cutting synthesis.

`index.md` and `log.md` are special generated files, not page types. The `tier` field is **orthogonal** to
`type` (content-shape vs lifecycle-stage as separate axes for Phase 4).

### Naming & linking

- Flat `wiki/pages/`, filename = kebab-case slug (`pages/andrej-karpathy.md`). Flat layout keeps
  cross-linking and Obsidian graph view simple; `index.md` provides by-category organization.
- Cross-references use **`[[slug-or-alias]]` wiki-links** (Obsidian-friendly), with the `related:`
  frontmatter list as the explicit, graph-ready complement. `lint` resolves both against slugs/aliases
  and flags broken ones. Both feed the Phase 2 graph.

---

## 4. CLI command surface

`llm-wiki` auto-discovers the wiki root by walking up to find `.llm-wiki.toml`; commands that need a wiki
fail with a clear message if none is found. Read/inspect commands take `--json`. Non-zero exit codes signal
failures so agents/CI can branch.

### Phase 1 verbs

| Command | Signature | Behavior |
|---|---|---|
| `init` | `init [PATH] [--target claude\|generic\|auto] [--root] [--hooks] [--force]` | Scaffold the tree, seed `index.md`/`log.md`, write `SCHEMA.md` + config, inject managed block, write slash commands (claude), optionally install hooks. Idempotent: re-run updates only the managed block; warns if `wiki/` exists (use `upgrade`). `--force` re-scaffolds over an existing `wiki/` (recreates seed/template files; still never deletes `pages/`/`inbox/` content). |
| `add-source` | `add-source <path\|url> [--title T] [--id ID]` | Vendor the raw source into `wiki/inbox/` (copy file / fetch URL), assign a source id, print it. Deterministic half of ingest. Skips if already present. |
| `new-page` | `new-page --type T --title "…" [--summary S] [--tags a,b] [--sources id…] [--slug S]` | Create `wiki/pages/<slug>.md` with full frontmatter (defaults filled, `created`/`updated` set) + per-type body template. Enforces unique slug. Prints path. Agent writes the prose. |
| `index` | `index [--check]` | Regenerate `index.md` from all pages' frontmatter, organized by type/category. `--check` verifies current (non-zero if stale). |
| `log` | `log <action> "<title>" [--source ID] [--page SLUG] [--note …]` | Append canonical `## [YYYY-MM-DD] <action> \| <title>` entry. Actions: `ingest\|query\|lint\|note\|edit\|init`. |
| `lint` | `lint [--fix] [--json]` | Structural checks (below). `--fix` repairs the safe subset; reports the rest for the agent. |
| `search` | `search "<query>" [--type T] [--tag X] [--limit N] [--json]` | BM25 over page text + frontmatter, grep fallback; ranked slugs + titles + snippets. |
| `doctor` | `doctor` | Health/setup check: tool vs `schema_version`, missing dirs, config validity, managed-block presence, hook status, embedding backend availability. Actionable diagnostics. |
| `status` | `status` | Quick content overview: page counts by type, last log entry, lint summary. |
| `upgrade` | `upgrade` | Refresh `SCHEMA.md`, templates, slash commands, managed block, hooks to installed `schema_version`; safe frontmatter migrations. Never touches content. |
| `version` | `version` | Print tool + schema version. |
| `install-hooks` / `uninstall-hooks` | — | Add/remove the opt-in hook entries in `.claude/settings.json` (idempotent, reversible). |
| `hook` | `hook <event>` | **Internal**, called by installed hooks (e.g. `post-edit`, `pre-edit`). Keeps hook logic in the upgradable package. |

### `lint` checks (Phase 1, structural)

Missing/invalid required frontmatter; unknown `type`; broken `[[wikilinks]]` and unresolved
`related`/`supersedes`/`contradicts` targets; orphan pages; duplicate slugs; `sources:` pointing at missing
`inbox/` files; stale pages (`review_by` past, or `updated` older than a configurable threshold); `index.md`
out of date; **structural contradiction hooks** (conflicting typed frontmatter, declared `contradicts:`).
The *semantic* contradiction pass is Phase 5.

### How verbs compose into the workflows

- **ingest:** `add-source` → *(agent reads)* → `new-page`×N → `index` → `log ingest` → `lint`
- **query:** `search` → *(agent synthesizes)* → optional `new-page` → `index` → `log query`
- **lint:** `lint --json` → *(agent reviews/fixes)* → `lint` again

### Reserved for later (named now to avoid clashes)

`embed` (Phase 3 vector indexing, distinct from `index`/the catalog), `similar` (Phase 3 semantic
near-duplicate detection), `graph` (Phase 2 traversal queries).

Global flags: `--wiki <dir>`, `--yes` (non-interactive; with no `--target`, defaults to `claude` if
`.claude/` exists else `generic`), `--quiet`. `--force` gates the few overwrite paths (currently `init`).

---

## 5. Agent integration

The **managed block** carries always-on guardrails (the invariants that stop an agent from corrupting the
wiki); `SCHEMA.md` carries the detailed playbooks (loaded on demand / imported).

### Managed block in `CLAUDE.md`/`AGENTS.md`

```markdown
<!-- BEGIN llm-wiki (managed) -->
## LLM Wiki
This project maintains an LLM wiki under `wiki/` via the `llm-wiki` CLI.
Full maintainer rules: @wiki/SCHEMA.md        (generic target: "see wiki/SCHEMA.md")

Invariants — do not violate:
- `wiki/index.md` and `wiki/log.md` are GENERATED. Never hand-edit; use `llm-wiki index` / `llm-wiki log`.
- `wiki/inbox/` is read-only raw sources. Add only via `llm-wiki add-source`.
- Create pages with `llm-wiki new-page` (correct frontmatter), never by hand.
- Before creating a page, `llm-wiki search` first — update an existing page rather than duplicate.
- After any wiki change, run `llm-wiki lint` (then `llm-wiki index`).

Maintain the wiki only when explicitly asked (e.g. /wiki-ingest, /wiki-query, /wiki-lint).
See @wiki/SCHEMA.md for the full ingest/query/lint workflows.
<!-- END llm-wiki (managed) -->
```

- **Claude target** uses `@wiki/SCHEMA.md` (Claude Code resolves the import → full schema effectively
  always in context). The block stays short.
- **Generic target** inlines a "see `wiki/SCHEMA.md`" pointer (no universal import mechanism), so the block
  is self-sufficient.

### `SCHEMA.md` (full playbook)

- Three-layer model + guardrails (expanded).
- **Page types** — when to use each + the per-type body template.
- **Frontmatter reference** — fields, required/optional, defaults (Section 3).
- **Naming & linking** — slugs, `[[wikilinks]]`, `related:`.
- **Workflows** — step-by-step Ingest / Query / Lint playbooks, each naming the exact `llm-wiki` verbs.
- **Customizing your wiki** — how to add page types, edit rules, adjust frontmatter or the stale threshold.

### Claude slash commands

`.claude/commands/wiki-{ingest,query,lint}.md` — thin prompt files invoked as `/wiki-ingest <path|url>`,
etc. Each restates the step sequence briefly **and** points at the `@wiki/SCHEMA.md` playbook (so they keep
working if the schema is customized). They call the same CLI verbs.

### Generic target

Identical guardrails + `SCHEMA.md`, no slash commands. When asked to ingest/query/lint, the agent reads the
`SCHEMA.md` playbook and runs the same verbs from prose. Same behavior, different ergonomics.

### Proactivity (explicit decision)

Phase 1: the agent maintains the wiki **only on explicit invocation** (slash command or direct request) —
no surprise background edits. A config toggle for proactive maintenance is deferred to Phase 5.

### Hooks (opt-in, Claude target)

Two **deterministic hygiene/guardrail** hooks, opt-in via `init --hooks` / `install-hooks`, default off:

- **`PostToolUse`** on `Edit|Write` matching `wiki/pages/**` → run `llm-wiki index` + `llm-wiki lint --json`,
  surfacing warnings to the agent. Makes "lint/index after a change" automatic.
- **`PreToolUse`** on `Edit|Write` matching `wiki/index.md`, `wiki/log.md`, `wiki/inbox/**` → **block** with a
  message ("use `llm-wiki log` / `add-source`"). Turns read-only/generated invariants into a hard gate.

Settings entries are **thin** — they call `llm-wiki hook <event>`, so behavior stays in the upgradable
package. `doctor` reports hook status. These hooks *enforce and report*; they do not proactively generate
content, so they are consistent with the explicit-only stance above. Proactive/semantic automation hooks
(SessionStart/Stop auto-ingest, session→episodic summarization, scheduled decay/re-lint, contradiction
resolution) stay in Phase 5. Hooks are Claude-specific; generic targets rely on the managed-block guardrails.

---

## 6. Error handling, testing, package structure

### Error handling (deterministic + actionable)

- **Discovery/setup:** no wiki found → `"No wiki found. Run llm-wiki init or pass --wiki <dir>."`; `init` on an
  existing wiki → warn + point to `upgrade`; tool older than the wiki's `schema_version` → refuse risky ops,
  point to `upgrade`/`doctor`.
- **Operations:** `add-source` URL/file failure → report, no partial write; `new-page` duplicate slug → error
  with a suggested slug; `lint` reports each issue per-file (with line where possible).
- **Safety:** managed-block and config writes are **surgical** (marker-bounded, preserve surrounding content);
  `index.md`/`log.md` writes are **atomic** (temp + rename); nothing destructive without `--force`.
- **Exit codes:** `0` ok, `1` error, `2` lint issues found (distinct so agents/CI can branch). `--json` emits
  structured errors.

### Testing (TDD — red→green→refactor)

`pytest` over a temp-wiki fixture (the CLI is deterministic and file-based):

- Per-command unit tests: `init` tree snapshot; `new-page` valid frontmatter + unique slug; `index`
  deterministic regen; `log` canonical format; **table-driven `lint`** (one case per violation class);
  `search` ranking; `add-source` (mocked network).
- **Idempotency:** managed-block injection run twice = identical + preserves user content;
  `install/uninstall-hooks` round-trips `settings.json` to original; `upgrade` refreshes templates without
  touching content.
- **Hooks:** `hook post-edit` triggers index+lint; `hook pre-edit` returns a block decision for protected paths.
- **Golden-file tests** for packaged templates (`SCHEMA.md`, slash commands) to catch drift.
- **One integration test:** full ingest sequence (`add-source → new-page → index → log → lint`) asserting end state.

### Package / repo structure (`init-llm-wiki`)

```
pyproject.toml          # PEP 621 + uv; entry point  llm-wiki = llm_wiki.cli:main
src/llm_wiki/
  cli.py                # Typer dispatch only
  config.py             # .llm-wiki.toml read/write + root discovery (walk-up)
  frontmatter.py        # schema model, parse/serialize, defaults, validation
  pages.py  catalog.py  log.py  lint.py  search.py  sources.py
  managed_block.py      # CLAUDE.md/AGENTS.md injection
  hooks.py              # install/uninstall + `hook <event>` dispatch
  scaffold.py  upgrade.py
  templates/            # SCHEMA.md, per-type page bodies, managed block, slash commands, config
tests/                  # conftest temp-wiki fixtures + per-module + integration
```

- **Stack:** Python ≥3.11 (stdlib `tomllib`), **Typer** for the CLI, `pyyaml` for frontmatter,
  `rank-bm25` for search. `networkx` is Phase 2; `sentence-transformers` + `sqlite-vec` are Phase 3
  optional extras. Deps stay lean.
- One module per concern (CLI just dispatches; templates separated from logic) — small, testable units.
- **Dev:** `uv tool install --editable .` → instant global `llm-wiki`. PyPI publish later.

---

## 7. Out of scope for Phase 1 (deferred)

- **Phase 2:** knowledge graph (`graph` verb, `networkx`, entity/relation extraction).
- **Phase 3:** vector embeddings (`embed`/`similar` verbs, local-first `sentence-transformers` + `sqlite-vec`,
  hybrid search with reciprocal rank fusion). Phase 1 only lays the seam: pluggable retriever interface,
  reserved `.index/`, content-hash tracking.
- **Phase 4:** memory lifecycle (confidence/decay/supersession), consolidation tiers. Phase 1 only carries the
  frontmatter fields, validated but inert.
- **Phase 5:** proactive/scheduled automation hooks, quality scoring, semantic contradiction detection +
  resolution, optional headless `--llm` ingest driver (B-mode).
- Multiple shipped use-case templates (`--template research|codebase|book|…`). Phase 1 ships one general
  template + a documented customization path; the `--template` hook may be stubbed but variants are deferred.

## 8. Decisions log

- **Form:** global versioned CLI + thin per-project scaffold (central logic auto-updates all wikis).
- **Stack:** Python + `uv`, PyPI later; single-executable packaging deferred (YAGNI).
- **Scope:** full v1 + v2, built in phases; Phase 1 first, lean, v2-ready.
- **Layout:** `wiki/` subdir + managed block in root `CLAUDE.md`/`AGENTS.md`; `--root` for dedicated repos.
- **Sources dir:** named `wiki/inbox/` (permanent, read-only), not `sources/`.
- **Templates:** one general `SCHEMA.md` + documented customization; `--template` variants deferred.
- **Architecture:** Approach A (thin LLM-free CLI + agent semantics); clean seam for optional B-mode later.
- **Embeddings (P3):** local-first (`sentence-transformers`), optional API (OpenAI/Voyage — not Anthropic);
  stored in `sqlite-vec` under gitignored `.index/`; incremental via content hash; markdown is source of truth.
- **Links:** `[[wikilink]]` primary + `related:` frontmatter; both feed the P2 graph.
- **Hooks:** opt-in hygiene/guardrail hooks in Phase 1 (Claude target), thin entries delegating to
  `llm-wiki hook <event>`; proactive automation deferred to Phase 5.
- **Proactivity:** explicit-invocation only in Phase 1.
