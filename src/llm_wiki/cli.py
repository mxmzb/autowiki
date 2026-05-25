from __future__ import annotations

import typer

from . import __version__

SCHEMA_VERSION = 1

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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
