# Configurable Wiki Update Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users choose whether wiki updates travel with code PRs or happen separately after merge, and preserve that choice through reinitialization and upgrades.

**Architecture:** Store a normalized `wiki_update_mode` in `WikiConfig`, resolve it at `autowiki init`, and pass it into managed-block rendering. Legacy configs load as `after_merge`; new and non-interactive installs default to `alongside_pr`; explicit CLI values can update an existing installation without `--force`.

**Tech Stack:** Python 3.13, Typer/Click, TOML, pytest

---

## File structure

- Modify `src/autowiki/config.py`: constants, normalization, persisted configuration, and legacy fallback.
- Modify `src/autowiki/managed_block.py`: mode-specific agent instructions.
- Modify `src/autowiki/scaffold.py`: carry the saved mode through creation and idempotent reinitialization.
- Modify `src/autowiki/cli.py`: flag, interactive selection, non-interactive default, and existing-install detection.
- Modify `src/autowiki/upgrade.py`: render from and persist the loaded mode.
- Modify `README.md`: document the installation choice and automation flag.
- Modify focused tests under `tests/`: regression coverage for config, rendering, scaffold, CLI, and upgrade behavior.

### Task 1: Persist and validate the update mode

**Files:**
- Modify: `tests/test_config.py`
- Modify: `src/autowiki/config.py`

- [ ] **Step 1: Add failing config tests**

Cover these exact behaviors:

```python
def test_new_config_defaults_to_alongside_pr(tmp_path: Path):
    assert WikiConfig(root=tmp_path / "wiki").wiki_update_mode == "alongside_pr"


def test_legacy_config_without_mode_loads_as_after_merge(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / CONFIG_NAME).write_text("[wiki]\nschema_version = 1\n")
    assert load_config(wiki).wiki_update_mode == "after_merge"


def test_wiki_update_mode_round_trip(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    write_config(WikiConfig(root=wiki, wiki_update_mode="after-merge"))
    assert load_config(wiki).wiki_update_mode == "after_merge"
    assert 'wiki_update_mode = "after_merge"' in (wiki / CONFIG_NAME).read_text()


def test_invalid_wiki_update_mode_fails_loudly(tmp_path: Path):
    with pytest.raises(ValueError, match="alongside_pr.*after_merge"):
        WikiConfig(root=tmp_path / "wiki", wiki_update_mode="sometimes")
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `uv run pytest tests/test_config.py -q`

Expected: failures because `WikiConfig` has no `wiki_update_mode` field.

- [ ] **Step 3: Implement normalized persisted configuration**

Add constants and normalization in `config.py`:

```python
ALONGSIDE_PR = "alongside_pr"
AFTER_MERGE = "after_merge"
WIKI_UPDATE_MODES = (ALONGSIDE_PR, AFTER_MERGE)


def normalize_wiki_update_mode(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    if normalized not in WIKI_UPDATE_MODES:
        accepted = ", ".join(WIKI_UPDATE_MODES)
        raise ValueError(f"wiki_update_mode must be one of: {accepted}")
    return normalized
```

Add `wiki_update_mode: str = ALONGSIDE_PR` and normalize it in
`WikiConfig.__post_init__`. Load a missing key as `AFTER_MERGE`; dump the field
immediately after `target`.

- [ ] **Step 4: Run config tests**

Run: `uv run pytest tests/test_config.py -q`

Expected: all config tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/autowiki/config.py tests/test_config.py
git commit -m "feat: persist wiki update mode"
```

### Task 2: Render one mode-specific managed workflow

**Files:**
- Modify: `tests/test_managed_block.py`
- Modify: `src/autowiki/managed_block.py`
- Modify: `src/autowiki/scaffold.py`
- Modify: `src/autowiki/upgrade.py`

- [ ] **Step 1: Add failing rendering tests**

Add assertions that `alongside_pr` contains `immediately before creating the PR`,
`create a draft PR`, `same branch`, and `Do not suggest a separate wiki ingest`,
while excluding `Always suggest on a merge`. Add the inverse test for
`after_merge`.

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `uv run pytest tests/test_managed_block.py -q`

Expected: failures because `render_block` does not accept or branch on the mode.

- [ ] **Step 3: Implement mode-specific rendering**

Change the signature to:

```python
def render_block(target: str, wiki_rel: str, wiki_update_mode: str) -> str:
```

Normalize the mode, select one publishing paragraph, and leave the invariants and
schema pointer shared. Pass `cfg.wiki_update_mode` from both scaffold and upgrade
call sites.

- [ ] **Step 4: Run rendering, scaffold, and upgrade tests**

Run:

```bash
uv run pytest tests/test_managed_block.py tests/test_scaffold.py tests/test_upgrade.py -q
```

Expected: all selected tests pass after updating direct `render_block` calls in
the tests with an explicit mode.

- [ ] **Step 5: Commit**

```bash
git add src/autowiki/managed_block.py src/autowiki/scaffold.py src/autowiki/upgrade.py tests/test_managed_block.py
git commit -m "feat: render mode-specific wiki workflow"
```

### Task 3: Select and change the mode through `autowiki init`

**Files:**
- Modify: `tests/test_scaffold.py`
- Create: `tests/test_cli_init.py`
- Modify: `src/autowiki/scaffold.py`
- Modify: `src/autowiki/cli.py`

- [ ] **Step 1: Add failing scaffold and CLI tests**

Cover:

- new `init_wiki` calls default to `alongside_pr`;
- reinitialization without a mode preserves the saved value;
- reinitialization with `wiki_update_mode="alongside-pr"` updates config and block;
- `--yes` defaults a new install to `alongside_pr`;
- `--wiki-update-mode after-merge` bypasses the prompt;
- interactive input `2` selects `after_merge`, while Enter selects
  `alongside_pr`;
- invalid CLI input exits nonzero before creating `wiki/`;
- an existing install does not prompt and preserves its choice.

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_scaffold.py tests/test_cli_init.py -q
```

Expected: failures because the scaffold parameter, CLI option, and prompt do not
exist.

- [ ] **Step 3: Implement scaffold update semantics**

Add `wiki_update_mode: str | None = None` to `init_wiki`. For an existing wiki
without `--force`, preserve the loaded value unless an explicit mode is supplied;
when supplied, normalize it, write the config, and regenerate the block. For new
or forced initialization, use the explicit value, then an existing saved value,
then `ALONGSIDE_PR` in that order.

- [ ] **Step 4: Implement CLI resolution**

Add `--wiki-update-mode` and a helper that:

1. validates an explicit value before mutation;
2. returns `None` for an existing install when no option was supplied;
3. returns `alongside_pr` for a new `--yes` install;
4. otherwise prompts with choices `1` and `2`, defaulting to `1`.

Catch `ValueError`, print the accepted values, and exit nonzero before calling
`init_wiki`.

- [ ] **Step 5: Run scaffold and CLI tests**

Run:

```bash
uv run pytest tests/test_scaffold.py tests/test_cli_init.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/autowiki/scaffold.py src/autowiki/cli.py tests/test_scaffold.py tests/test_cli_init.py
git commit -m "feat: choose wiki update mode during init"
```

### Task 4: Preserve migration behavior and document the option

**Files:**
- Modify: `tests/test_upgrade.py`
- Modify: `README.md`

- [ ] **Step 1: Add migration regression tests**

Add one test that removes `wiki_update_mode` from a legacy config, upgrades it,
and asserts explicit `after_merge` plus the separate workflow. Add another that
upgrades an `alongside_pr` config and asserts both config and managed block retain
the integrated workflow.

- [ ] **Step 2: Run upgrade tests and confirm the regressions pass or expose gaps**

Run: `uv run pytest tests/test_upgrade.py -q`

Expected: tests pass if Tasks 1–3 fully wired upgrade; otherwise fix only the
missing upgrade propagation.

- [ ] **Step 3: Document the installation choice**

Update the README quick start to show the interactive choice and
`--wiki-update-mode alongside-pr|after-merge` for scripts, including the legacy
compatibility rule in one sentence.

- [ ] **Step 4: Run the complete quality gate**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Expected: all tests pass and Ruff reports no lint or formatting changes needed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_upgrade.py README.md
git commit -m "docs: explain wiki update mode"
```

### Task 5: Prepare the pull request

**Files:**
- Verify all committed files from Tasks 1–4.

- [ ] **Step 1: Review the branch diff and commit history**

Run:

```bash
git diff --check origin/main...HEAD
git diff --stat origin/main...HEAD
git log --oneline origin/main..HEAD
```

Expected: only the design, plan, implementation, tests, and README changes for
the configurable wiki update mode.

- [ ] **Step 2: Push and create a ready PR**

Push `codex/wiki-update-mode` and create a ready PR describing the two modes,
legacy behavior, interactive/non-interactive selection, and verification.
