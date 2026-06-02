from __future__ import annotations

from importlib.resources import files


def load_template(name: str) -> str:
    """Read a packaged template asset from autowiki/templates/."""
    resource = files("autowiki").joinpath("templates", name)
    return resource.read_text(encoding="utf-8")


def page_template_name(page_type: str) -> str:
    return f"page_{page_type}.md"
