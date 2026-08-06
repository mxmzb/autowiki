# Configurable wiki update mode design

## Problem

Autowiki currently injects one fixed publishing workflow into every managed
agent-instruction block: suggest wiki ingestion around PR creation and again
after merge. Teams that want wiki changes to land with the code therefore end up
creating a second documentation-only PR after the feature has already merged.

The managed block is owned and refreshed by autowiki, so editing an individual
repository's `AGENTS.md` or `CLAUDE.md` is not durable. The publishing policy must
be an autowiki configuration choice.

## Decision

Add a persisted `wiki_update_mode` setting with two values:

- `alongside_pr`: ask whether to include wiki ingestion immediately before
  creating a code PR. When accepted, create a draft PR for a stable source URL,
  ingest the PR, commit and push the wiki changes to the same branch, then mark
  the PR ready and continue normally. Do not suggest another ingest after merge.
- `after_merge`: keep wiki ingestion separate and suggest it after substantial
  work, especially after a PR or branch merges.

New interactive installations ask the user to choose. New non-interactive
installations default to `alongside_pr`. Existing installations that lack the
field load as `after_merge`, preserving their current behavior until changed.

## Configuration

Persist the selection in `.autowiki.toml`:

```toml
[wiki]
wiki_update_mode = "alongside_pr"
```

`WikiConfig` validates and carries the setting. Config loading uses
`after_merge` only when reading a legacy file without the key; newly constructed
configuration uses `alongside_pr`. Config dumping always writes the key so the
choice becomes explicit after initialization or upgrade.

Invalid mode values fail loudly with a message listing the two accepted values.

## CLI behavior

`autowiki init` gains:

```text
--wiki-update-mode alongside-pr|after-merge
```

For a new interactive installation without the flag, prompt:

```text
How should agents handle wiki updates?
  1. Alongside code PRs (recommended)
  2. Separately after code PRs merge
```

Choosing Enter or running with `--yes` selects `alongside_pr`. Supplying the
option bypasses the prompt and works in scripts.

Re-running `autowiki init` against an existing wiki without the option preserves
its saved choice and does not prompt. Re-running it with the option updates only
that choice as part of the normal idempotent managed-block refresh; `--force` is
not required.

## Managed instructions

`render_block` receives the persisted mode and renders one unambiguous workflow.
Both modes retain all existing wiki structural invariants and the pointer to
`SCHEMA.md`.

For `alongside_pr`, the instruction must cover:

- asking immediately before PR creation unless the user already chose;
- accepting via a temporary draft PR and same-branch wiki commit;
- declining and publishing normally;
- leaving the PR in draft if ingestion fails until fixed or explicitly skipped;
- not suggesting a separate post-merge ingest.

For `after_merge`, the instruction must retain the current separate suggestion
behavior without mentioning the draft-PR workflow.

All initialization, reinitialization, and upgrade paths render the block from the
saved mode. `autowiki upgrade` migrates a legacy missing value to explicit
`after_merge`, so an upgrade does not silently change established behavior.

## Foyer adoption

After releasing or otherwise using the updated autowiki CLI, Foyer selects:

```bash
autowiki init . --wiki-update-mode alongside-pr
```

That command updates `wiki/.autowiki.toml` and refreshes the managed block in
`AGENTS.md`. The repository-specific result is a small adoption PR; future
upgrades preserve it.

## Testing

- Config tests cover new defaults, legacy missing-key behavior, round trips, and
  invalid values.
- Managed-block tests assert mode-specific text and absence of the other mode's
  workflow.
- Scaffold tests cover new installation, idempotent reinitialization, and an
  explicit mode change.
- CLI tests cover the interactive selection, Enter/`--yes` default, explicit
  option, and invalid option.
- Upgrade tests prove legacy installations remain `after_merge` and configured
  installations retain their choice.
- Existing test suites remain green.

## Failure handling

The CLI validates the mode before mutating repository files. A failed prompt or
invalid flag leaves the installation unchanged. Upgrade and reinitialization use
the loaded configuration as their source of truth rather than inferring policy
from existing prose.

## Non-goals

- Enforcing wiki participation in CI.
- Automatically deciding whether a particular PR deserves ingestion.
- Changing the wiki schema, page types, or ingest mechanics.
- Automating GitHub operations inside the autowiki CLI; the managed instructions
  continue to guide the coding agent through those operations.
