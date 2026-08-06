from __future__ import annotations

from pathlib import Path

from . import config as cfgmod
from .assets import load_template
from .config import WikiConfig
from .frontmatter import today
from .hooks import install_hooks
from .managed_block import render_block, upsert_block

_SLASH_COMMANDS = ("wiki-ingest", "wiki-query", "wiki-lint")


def project_root_of(cfg: WikiConfig) -> tuple[Path, bool]:
    """Return (project_root, root_mode) for a wiki config.

    Uses the persisted `root_layout` flag (not the directory name), so a --root
    wiki in a directory literally named "wiki" is still resolved correctly.
    Root layout: cfg.root is the project itself. Default layout: project is the parent.
    """
    if cfg.root_layout:
        return cfg.root, True
    return cfg.root.parent, False


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


def _write_if_absent(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _ensure_gitignore_line(path: Path, line: str) -> None:
    """Ensure `line` is present in a .gitignore, preserving any existing content.

    Critical for --root mode, where the .gitignore is the project's own file and
    must never be clobbered.
    """
    if not path.exists():
        path.write_text(line + "\n", encoding="utf-8")
        return
    existing = path.read_text(encoding="utf-8")
    if line in {ln.strip() for ln in existing.splitlines()}:
        return
    sep = "" if existing == "" or existing.endswith("\n") else "\n"
    path.write_text(existing + sep + line + "\n", encoding="utf-8")


# Known per-provider agent instruction files. Multiple may coexist (e.g. a repo
# that supports both Claude and the generic AGENTS convention); we keep them in sync.
_INSTRUCTION_FILES = ("CLAUDE.md", "AGENTS.md", "GEMINI.md")


def _claude_present(project_root: Path) -> bool:
    """Whether a Claude harness is set up here (independent of the block's home)."""
    return (project_root / ".claude").exists() or (project_root / "CLAUDE.md").exists()


def _instruction_targets(project_root: Path, target: str) -> list[Path]:
    """Instruction files to upsert the managed block into.

    Always the primary file for `target`, plus any other known provider file that
    already exists. Paths are deduped by their canonical (symlink-resolved) target,
    so a `CLAUDE.md -> AGENTS.md` symlink is written once — to the canonical file —
    rather than duplicating the block.
    """
    primary = "CLAUDE.md" if target == "claude" else "AGENTS.md"
    candidates = [project_root / primary]
    candidates += [
        project_root / name
        for name in _INSTRUCTION_FILES
        if name != primary and (project_root / name).exists()
    ]
    seen: set[Path] = set()
    targets: list[Path] = []
    for path in candidates:
        canonical = path.resolve()
        if canonical in seen:
            continue
        seen.add(canonical)
        targets.append(path)
    return targets


def _write_managed_block(project_root: Path, cfg: WikiConfig, root_mode: bool) -> None:
    wiki_rel = "" if root_mode else "wiki/"
    block = render_block(cfg.target, wiki_rel, cfg.wiki_update_mode)
    for path in _instruction_targets(project_root, cfg.target):
        upsert_block(path, block)


def init_wiki(
    project_root: Path,
    target: str = "claude",
    root_mode: bool = False,
    force: bool = False,
    with_hooks: bool = False,
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
        if with_hooks:
            install_hooks(project_root)
        return cfg, "updated"

    (wiki_root / "inbox").mkdir(parents=True, exist_ok=True)
    (wiki_root / "pages").mkdir(parents=True, exist_ok=True)
    (wiki_root / ".index").mkdir(parents=True, exist_ok=True)
    _touch(wiki_root / "inbox" / ".gitkeep")
    _touch(wiki_root / "pages" / ".gitkeep")

    cfg = WikiConfig(root=wiki_root, target=target, root_layout=root_mode)
    cfgmod.write_config(cfg)
    (wiki_root / "SCHEMA.md").write_text(load_template("SCHEMA.md"), encoding="utf-8")
    _ensure_gitignore_line(wiki_root / ".gitignore", ".index/")
    _write_if_absent(wiki_root / "index.md", "# Index\n\n_No pages yet._\n")
    _write_if_absent(
        wiki_root / "log.md", f"# Log\n\n## [{today()}] init | wiki initialized\n"
    )

    _write_managed_block(project_root, cfg, root_mode)

    # Slash commands are a Claude-harness feature: install them when targeting
    # claude OR when a Claude harness is present, even if the block lives in AGENTS.md.
    if target == "claude" or _claude_present(project_root):
        cmd_dir = project_root / ".claude" / "commands"
        cmd_dir.mkdir(parents=True, exist_ok=True)
        for name in _SLASH_COMMANDS:
            (cmd_dir / f"{name}.md").write_text(
                load_template(f"command_{name}.md"), encoding="utf-8"
            )

    # --hooks is an explicit opt-in; honor it regardless of target.
    if with_hooks:
        install_hooks(project_root)

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
