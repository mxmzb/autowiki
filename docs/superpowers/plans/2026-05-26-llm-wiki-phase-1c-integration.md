# LLM Wiki Phase 1 — Milestone C: Hooks, doctor/status, upgrade Implementation Plan

> **Execution note:** Inline TDD by the controller, commit per task, single holistic review at the end (same as Milestone B).

**Goal:** Complete Phase 1 with the opt-in Claude hooks (hygiene/guardrail), the `doctor` and `status` commands, and `upgrade` — plus broader integration coverage.

**Architecture:** New modules `hooks.py` (settings.json install/uninstall + `hook <event>` dispatch), `doctor.py` (health + content overview), `upgrade.py` (refresh templates/block/commands + schema bump + frontmatter migration). `cli.py` gains `install-hooks`/`uninstall-hooks`/`hook`/`doctor`/`status`/`upgrade` and an `--hooks` flag on `init`. All deterministic; hooks delegate to the global `llm-wiki` so behavior stays upgradable.

**Tech Stack:** Python ≥3.11, Typer, stdlib `json`, `pytest`.

**Spec reference:** Section 5 (hooks) and Section 4 (`doctor`/`status`/`upgrade`) of the design spec.

---

## Task C1: `hooks.py` — install/uninstall + run_hook

**Files:** Create `src/llm_wiki/hooks.py`; Test `tests/test_hooks.py`. Add `project_root_of(cfg)` helper to `scaffold.py`.

- [ ] `project_root_of(cfg) -> tuple[Path, bool]` in `scaffold.py`: `(cfg.root.parent, False)` if `cfg.root.name == "wiki"` else `(cfg.root, True)` (project_root, root_mode).
- [ ] In `hooks.py`:
  - Constants: `HOOK_PREFIX = "llm-wiki hook"`; desired entries for `PreToolUse` and `PostToolUse`, matcher `"Edit|Write"`, commands `llm-wiki hook pre-edit` / `llm-wiki hook post-edit`.
  - `install_hooks(project_root)`: load `.claude/settings.json` (`{}` if absent), under `hooks[event]` strip any existing `llm-wiki hook` entries then append ours; write pretty JSON. Idempotent.
  - `uninstall_hooks(project_root)`: strip our entries from every event, drop empty event lists and an empty `hooks` key; write. Reversible (only touches our entries).
  - `hooks_installed(project_root) -> bool`.
  - `run_hook(cfg_finder, event, stdin_text) -> tuple[int, str]` — pure/testable (returns exit code + message, does no I/O to sys):
    - parse `stdin_text` JSON; get `file_path` from `tool_input`. No/invalid path → `(0, "")` (never block on junk).
    - **pre-edit:** resolve the wiki for that file; if `file_path` is `index.md`, `log.md`, or under `inbox/` → `(2, "blocked: <name> is generated/read-only — use llm-wiki index/log/add-source")`; else `(0, "")`.
    - **post-edit:** if `file_path` is under `pages/` → `write_index(cfg)` + `run_lint(cfg)`, return `(0, "<n> lint issue(s): ...")` (non-blocking); else `(0, "")`.
- [ ] Tests: install creates settings with both hooks; install twice = identical (idempotent); uninstall after install restores a pre-existing settings dict; `run_hook("pre-edit", …index.md…)` → exit 2; `run_hook("pre-edit", …pages/x.md…)` → 0; `run_hook("post-edit", …pages/x.md…)` rebuilds index and returns 0; junk stdin → 0.

## Task C2: wire hooks into the CLI + `init --hooks`

**Files:** Modify `src/llm_wiki/cli.py`, `src/llm_wiki/scaffold.py`; Test `tests/test_cli_hooks.py`.

- [ ] `init_wiki(..., with_hooks=False)`: if `with_hooks and target == "claude"`, call `install_hooks(project_root)` after writing commands. Add `--hooks` option to the `init` command.
- [ ] CLI commands: `install-hooks` / `uninstall-hooks` (resolve cfg → `project_root_of` → install/uninstall, echo result); `hook <event>` (read stdin, call `run_hook`, echo message to stdout if exit 0 else stderr, `raise typer.Exit(code)`).
- [ ] Tests (CliRunner): `init --hooks --target claude` writes hooks into `.claude/settings.json`; `hook pre-edit` with index.md JSON on stdin exits 2; `uninstall-hooks` removes them.

## Task C3: `doctor.py` — doctor + status

**Files:** Create `src/llm_wiki/doctor.py`; Modify `cli.py`; Test `tests/test_doctor.py`.

- [ ] `doctor(cfg) -> list[tuple[str, str]]` (level `ok|warn|error`, message): schema_version vs `SCHEMA_VERSION` (warn if wiki older → run upgrade; error if tool older); presence of `pages/`, `inbox/`, `SCHEMA.md`, `index.md`, `log.md`; managed block present in the project's `CLAUDE.md`/`AGENTS.md`; hooks installed (info); embedding provider (info). 
- [ ] `status(cfg) -> dict`: `{counts: {type: n}, total, last_log, lint_errors, lint_warnings}` (counts from page frontmatter; last_log = last `## [` line; lint counts from `run_lint`).
- [ ] CLI `doctor` (print findings; exit 1 if any error) and `status` (print summary).
- [ ] Tests: a healthy wiki → doctor has no error; deleting `SCHEMA.md` → doctor reports an error; status counts pages by type and reports totals.

## Task C4: `upgrade.py`

**Files:** Create `src/llm_wiki/upgrade.py`; Modify `cli.py`; Test `tests/test_upgrade.py`.

- [ ] `upgrade(cfg) -> None`: preserve user config (target/extra_types/stale_days/embedding_provider); rewrite `SCHEMA.md` from template; rewrite slash commands if claude target; refresh managed block (`scaffold._write_managed_block` via `project_root_of`); refresh hooks if installed; bump `cfg.schema_version = SCHEMA_VERSION` and `write_config`; migrate page frontmatter (re-`parse`/`dump` each page). NEVER touch `inbox/`, page bodies, `index.md`/`log.md` content.
- [ ] CLI `upgrade` (echo a short summary of what was refreshed).
- [ ] Tests: editing SCHEMA.md then `upgrade` restores the canonical template; `extra_types`/`stale_days` survive upgrade; a page missing a (newer) frontmatter field gets it after upgrade; `index.md`/`log.md`/inbox content untouched.

## Task C5: integration sweep + version bump

**Files:** Test `tests/test_integration_phase1.py`; maybe bump package version.

- [ ] One end-to-end integration test exercising init(--hooks) → add-source → new-page → index → log → lint → search → status → doctor → upgrade, asserting a coherent final state.
- [ ] Confirm `uv run pytest` green and `llm-wiki --help` lists every command. Confirm `uv build` clean.

---

## After Milestone C
Phase 1 is complete. Phases 2–5 (knowledge graph, hybrid/vector search, memory lifecycle, automation/quality) follow, each its own spec → plan cycle.
