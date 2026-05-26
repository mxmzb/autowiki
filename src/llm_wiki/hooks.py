from __future__ import annotations

import copy
import json
from pathlib import Path

from .catalog import index_is_current, write_index
from .config import find_wiki_root, load_config
from .lifecycle import review
from .lint import run_lint
from .sources import pending_sources

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
    # Proactive: surface what needs attention to the agent at session start.
    "SessionStart": {
        "hooks": [{"type": "command", "command": "llm-wiki hook session-start"}],
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


def _session_summary(cfg) -> str:
    """A short 'what needs attention' line for the SessionStart hook (empty if nothing)."""
    parts = []
    pending = len(pending_sources(cfg))
    if pending:
        parts.append(f"{pending} source(s) awaiting ingest")
    due = len(review(cfg))
    if due:
        parts.append(f"{due} page(s) due for review")
    errors = sum(1 for i in run_lint(cfg) if i.level == "error")
    if errors:
        parts.append(f"{errors} lint error(s)")
    if not index_is_current(cfg):
        parts.append("index stale")
    if not parts:
        return ""
    return "llm-wiki: " + ", ".join(parts) + ". Run /wiki-ingest for pending sources and /wiki-lint to fix issues."


def run_hook(event: str, stdin_text: str) -> tuple[int, str]:
    """Dispatch a hook event. Returns (exit_code, message). Never raises on bad input."""
    try:
        data = json.loads(stdin_text) if stdin_text.strip() else {}
    except json.JSONDecodeError:
        return (0, "")
    if not isinstance(data, dict):
        return (0, "")  # non-object payload (array/scalar/null) — never block

    if event == "session-start":
        cwd = data.get("cwd")
        start = Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()
        root = find_wiki_root(start)
        if root is None:
            return (0, "")
        return (0, _session_summary(load_config(root)))

    tool_input = data.get("tool_input")
    file_path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(file_path, str) or not file_path:
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
