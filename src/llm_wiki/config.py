from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .frontmatter import PAGE_TYPES

CONFIG_NAME = ".llm-wiki.toml"
SCHEMA_VERSION = 1


@dataclass
class WikiConfig:
    root: Path  # dir containing pages/, inbox/, index.md, log.md, SCHEMA.md
    schema_version: int = SCHEMA_VERSION
    target: str = "claude"  # "claude" | "generic"
    embedding_provider: str = "local"
    stale_days: int = 365
    extra_types: list[str] = field(default_factory=list)

    @property
    def allowed_types(self) -> tuple[str, ...]:
        """Built-in page types plus any user-defined extra_types."""
        return tuple(PAGE_TYPES) + tuple(self.extra_types)

    @property
    def pages_dir(self) -> Path:
        return self.root / "pages"

    @property
    def inbox_dir(self) -> Path:
        return self.root / "inbox"

    @property
    def index_file(self) -> Path:
        return self.root / "index.md"

    @property
    def log_file(self) -> Path:
        return self.root / "log.md"

    @property
    def schema_file(self) -> Path:
        return self.root / "SCHEMA.md"

    @property
    def index_dir(self) -> Path:
        return self.root / ".index"

    @property
    def config_file(self) -> Path:
        return self.root / CONFIG_NAME


def find_wiki_root(start: Path) -> Path | None:
    """Locate a wiki root from `start`, walking up.

    At each level, `d` itself may be the wiki root (root layout), or it may be a
    project containing a `wiki/` subdir (default layout) — so running a command
    from the project root finds the wiki without needing to cd into it.
    """
    start = start.resolve()
    for d in (start, *start.parents):
        if (d / CONFIG_NAME).is_file():
            return d
        if (d / "wiki" / CONFIG_NAME).is_file():
            return d / "wiki"
    return None


def load_config(root: Path) -> WikiConfig:
    data = tomllib.loads((root / CONFIG_NAME).read_text(encoding="utf-8"))
    wiki = data.get("wiki", {})
    return WikiConfig(
        root=root,
        schema_version=wiki.get("schema_version", SCHEMA_VERSION),
        target=wiki.get("target", "claude"),
        embedding_provider=wiki.get("embedding_provider", "local"),
        stale_days=wiki.get("stale_days", 365),
        extra_types=list(wiki.get("extra_types", [])),
    )


def dump_config(cfg: WikiConfig) -> str:
    extra = ", ".join(f'"{t}"' for t in cfg.extra_types)
    return (
        "[wiki]\n"
        f"schema_version = {cfg.schema_version}\n"
        f'target = "{cfg.target}"\n'
        f'embedding_provider = "{cfg.embedding_provider}"\n'
        f"stale_days = {cfg.stale_days}\n"
        f"extra_types = [{extra}]\n"
    )


def write_config(cfg: WikiConfig) -> None:
    cfg.config_file.write_text(dump_config(cfg), encoding="utf-8")
