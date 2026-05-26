from __future__ import annotations

import copy
import json
from pathlib import Path

from .catalog import write_index
from .config import find_wiki_root, load_config
from .lint import run_lint

HOOK_PREFIX = "llm-wiki hook"

# Thin settings.json entries — the behavior lives in `llm-wiki hook <event>` so it
# stays upgradable with the package.
_DESIRED = {
    "PreToolUse": {
        "matcher": "Edit|Write",
        "hooks": [{"type": "command", "command": "llm-wiki hook pre-edit"}],
    },
    "PostToolUse": {
        "matcher": "Edit|Write",
        "hooks": [{"type": "command", "command": "llm-wiki hook post-edit"}],
    },
}


def _settings_path(project_root: Path) -> Path:
    return project_root / ".claude" / "settings.json"


def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _strip_ours(groups: list) -> list:
    """Drop our hook commands from each matcher group; drop groups left empty."""
    out = []
    for group in groups:
        hooks_list = group.get("hooks", [])
        if not hooks_list:
            out.append(group)
            continue
        kept = [h for h in hooks_list if not str(h.get("command", "")).startswith(HOOK_PREFIX)]
        if kept:
            out.append({**group, "hooks": kept})
        # else: the group held only our hook → drop it
    return out


def install_hooks(project_root: Path) -> None:
    """Install the opt-in hygiene/guardrail hooks into .claude/settings.json (idempotent)."""
    path = _settings_path(project_root)
    data = _load(path)
    hooks = data.setdefault("hooks", {})
    for event, entry in _DESIRED.items():
        groups = _strip_ours(hooks.get(event, []))
        groups.append(copy.deepcopy(entry))
        hooks[event] = groups
    _write(path, data)


def uninstall_hooks(project_root: Path) -> None:
    """Remove our hooks, leaving any other settings untouched (reversible)."""
    path = _settings_path(project_root)
    if not path.exists():
        return
    data = _load(path)
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return
    for event in list(hooks.keys()):
        hooks[event] = _strip_ours(hooks[event])
        if not hooks[event]:
            del hooks[event]
    if not hooks:
        data.pop("hooks", None)
    _write(path, data)


def hooks_installed(project_root: Path) -> bool:
    hooks = _load(_settings_path(project_root)).get("hooks", {})
    for groups in hooks.values():
        for group in groups:
            for h in group.get("hooks", []):
                if str(h.get("command", "")).startswith(HOOK_PREFIX):
                    return True
    return False


def run_hook(event: str, stdin_text: str) -> tuple[int, str]:
    """Dispatch a hook event. Returns (exit_code, message). Never raises on bad input."""
    try:
        data = json.loads(stdin_text) if stdin_text.strip() else {}
    except json.JSONDecodeError:
        return (0, "")
    file_path = (data.get("tool_input") or {}).get("file_path")
    if not file_path:
        return (0, "")

    fp = Path(file_path).resolve()
    root = find_wiki_root(fp.parent)
    if root is None:
        return (0, "")  # not inside a wiki — never block
    cfg = load_config(root)

    if event == "pre-edit":
        protected = {cfg.index_file.resolve(), cfg.log_file.resolve()}
        if fp in protected or cfg.inbox_dir.resolve() in fp.parents:
            return (
                2,
                f"blocked: {fp.name} is generated/read-only — use "
                f"`llm-wiki index` / `llm-wiki log` / `llm-wiki add-source`.",
            )
        return (0, "")

    if event == "post-edit":
        if cfg.pages_dir.resolve() in fp.parents:
            write_index(cfg)
            issues = run_lint(cfg)
            errors = sum(1 for i in issues if i.level == "error")
            if issues:
                return (
                    0,
                    f"llm-wiki: index rebuilt; lint found {errors} error(s), "
                    f"{len(issues) - errors} warning(s). Run `llm-wiki lint`.",
                )
            return (0, "llm-wiki: index rebuilt; lint clean.")
        return (0, "")

    return (0, "")
