from __future__ import annotations

from pathlib import Path

from . import config as cfgmod
from .assets import load_template
from .config import WikiConfig
from .frontmatter import today
from .managed_block import render_block, upsert_block

_SLASH_COMMANDS = ("wiki-ingest", "wiki-query", "wiki-lint")


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


def _write_if_absent(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _write_managed_block(project_root: Path, cfg: WikiConfig, root_mode: bool) -> None:
    wiki_rel = "" if root_mode else "wiki/"
    block = render_block(cfg.target, wiki_rel)
    fname = "CLAUDE.md" if cfg.target == "claude" else "AGENTS.md"
    upsert_block(project_root / fname, block)


def init_wiki(
    project_root: Path,
    target: str = "claude",
    root_mode: bool = False,
    force: bool = False,
) -> tuple[WikiConfig, str]:
    """Scaffold a wiki. Returns (config, action) where action is created|recreated|updated."""
    project_root = Path(project_root).resolve()
    wiki_root = project_root if root_mode else project_root / "wiki"
    existed = (wiki_root / cfgmod.CONFIG_NAME).exists()

    if existed and not force:
        # Idempotent re-init: refresh only the managed block, keeping the wiki's
        # originally-chosen target (a re-init does not switch claude <-> generic).
        cfg = cfgmod.load_config(wiki_root)
        _write_managed_block(project_root, cfg, root_mode)
        return cfg, "updated"

    (wiki_root / "inbox").mkdir(parents=True, exist_ok=True)
    (wiki_root / "pages").mkdir(parents=True, exist_ok=True)
    (wiki_root / ".index").mkdir(parents=True, exist_ok=True)
    _touch(wiki_root / "inbox" / ".gitkeep")
    _touch(wiki_root / "pages" / ".gitkeep")

    cfg = WikiConfig(root=wiki_root, target=target)
    cfgmod.write_config(cfg)
    (wiki_root / "SCHEMA.md").write_text(load_template("SCHEMA.md"), encoding="utf-8")
    (wiki_root / ".gitignore").write_text(".index/\n", encoding="utf-8")
    _write_if_absent(wiki_root / "index.md", "# Index\n\n_No pages yet._\n")
    _write_if_absent(
        wiki_root / "log.md", f"# Log\n\n## [{today()}] init | wiki initialized\n"
    )

    _write_managed_block(project_root, cfg, root_mode)

    if target == "claude":
        cmd_dir = project_root / ".claude" / "commands"
        cmd_dir.mkdir(parents=True, exist_ok=True)
        for name in _SLASH_COMMANDS:
            (cmd_dir / f"{name}.md").write_text(
                load_template(f"command_{name}.md"), encoding="utf-8"
            )

    return cfg, ("recreated" if existed else "created")


def resolve_target(project_root: Path, target: str, assume_yes: bool) -> str:
    """Resolve --target auto into claude|generic by detecting project conventions."""
    if target in ("claude", "generic"):
        return target
    project_root = Path(project_root)
    has_claude = (project_root / ".claude").exists() or (project_root / "CLAUDE.md").exists()
    has_agents = (project_root / "AGENTS.md").exists()
    if has_claude:
        return "claude"
    if has_agents:
        return "generic"
    return "claude"  # no-signal default; interactive prompting omitted in this milestone
