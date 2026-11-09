"""Every third-party module autowiki imports must be a declared dependency.

Regression: cli.py imports click directly, but only typer was declared. The
locked typer (0.25) pulled click in transitively, so the dev venv worked, while
`uv tool install` resolved typer 0.28, which no longer depends on click, and
the installed `autowiki` crashed with ModuleNotFoundError on every invocation.
"""

import ast
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Import name -> distribution name, where they differ.
DISTRIBUTION_FOR_MODULE = {"yaml": "pyyaml"}


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _declared(requirements: list[str]) -> set[str]:
    return {_normalize(re.split(r"[\s<>=!~;\[]", r, maxsplit=1)[0]) for r in requirements}


def _third_party_imports() -> set[str]:
    modules: set[str] = set()
    for path in (ROOT / "src" / "autowiki").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                modules |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                modules.add(node.module.split(".")[0])
    return {m for m in modules if m not in sys.stdlib_module_names and m != "autowiki"}


def test_every_third_party_import_is_declared():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    declared = _declared(project["dependencies"])
    for extra in project.get("optional-dependencies", {}).values():
        declared |= _declared(extra)

    missing = sorted(
        module
        for module in _third_party_imports()
        if _normalize(DISTRIBUTION_FOR_MODULE.get(module, module)) not in declared
    )
    assert missing == [], f"imported but not declared in pyproject.toml: {missing}"
