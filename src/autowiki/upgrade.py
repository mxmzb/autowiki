from __future__ import annotations

from .assets import load_template
from .config import SCHEMA_VERSION, WikiConfig, write_config
from .frontmatter import dump, parse
from .hooks import hooks_installed, install_hooks
from .managed_block import render_block, upsert_block
from .pages import list_page_paths
from .scaffold import _SLASH_COMMANDS, _ensure_gitignore_line, project_root_of


def upgrade(cfg: WikiConfig) -> dict:
    """Refresh templates/commands/block/hooks to the current schema version and
    migrate page frontmatter, preserving user config and all content."""
    project_root, root_mode = project_root_of(cfg)

    # Ensure derived-data dir is present and ignored (older wikis predate Phase 3).
    _ensure_gitignore_line(cfg.root / ".gitignore", ".index/")
    cfg.index_dir.mkdir(parents=True, exist_ok=True)

    # Refresh the maintainer schema.
    cfg.schema_file.write_text(load_template("SCHEMA.md"), encoding="utf-8")

    # Refresh slash commands (claude target).
    commands = 0
    if cfg.target == "claude":
        cmd_dir = project_root / ".claude" / "commands"
        cmd_dir.mkdir(parents=True, exist_ok=True)
        for name in _SLASH_COMMANDS:
            (cmd_dir / f"{name}.md").write_text(load_template(f"command_{name}.md"), encoding="utf-8")
            commands += 1

    # Refresh the managed block.
    wiki_rel = "" if root_mode else "wiki/"
    block_file = project_root / ("CLAUDE.md" if cfg.target == "claude" else "AGENTS.md")
    upsert_block(block_file, render_block(cfg.target, wiki_rel))

    # Refresh hooks only if they were already installed.
    hooks_refreshed = False
    if cfg.target == "claude" and hooks_installed(project_root):
        install_hooks(project_root)
        hooks_refreshed = True

    # Migrate page frontmatter (re-dump to pick up new default fields); body preserved.
    migrated = 0
    for path in list_page_paths(cfg):
        try:
            fm, body = parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue  # leave unparseable pages for lint to report
        path.write_text(dump(fm, body), encoding="utf-8")
        migrated += 1

    # Bump schema version, preserving every other config field.
    cfg.schema_version = SCHEMA_VERSION
    write_config(cfg)

    return {"commands": commands, "hooks_refreshed": hooks_refreshed, "pages_migrated": migrated}
