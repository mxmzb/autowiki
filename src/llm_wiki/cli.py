from __future__ import annotations

from pathlib import Path

import typer

from . import __version__
from .config import SCHEMA_VERSION
from .scaffold import init_wiki, resolve_target

app = typer.Typer(
    help="Initialize and maintain Karpathy-style LLM wikis.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root() -> None:
    """Initialize and maintain Karpathy-style LLM wikis."""


@app.command()
def version() -> None:
    """Print the llm-wiki tool and schema version."""
    typer.echo(f"llm-wiki {__version__} (schema v{SCHEMA_VERSION})")


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Project directory to initialize."),
    target: str = typer.Option("auto", help="auto|claude|generic"),
    root: bool = typer.Option(False, "--root", help="Place the wiki at the project root."),
    force: bool = typer.Option(
        False,
        "--force",
        help="Refresh templates/config over an existing wiki (never overwrites index.md, log.md, pages, or inbox).",
    ),
    yes: bool = typer.Option(False, "--yes", help="Non-interactive."),
) -> None:
    """Initialize an LLM wiki in PATH (new or existing project)."""
    resolved = resolve_target(path, target, yes)
    cfg, action = init_wiki(path, target=resolved, root_mode=root, force=force)
    typer.echo(f"Wiki {action} at {cfg.root} (target: {cfg.target})")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
