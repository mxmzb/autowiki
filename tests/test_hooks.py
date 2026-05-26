import json
from pathlib import Path

from llm_wiki.catalog import index_is_current
from llm_wiki.config import WikiConfig
from llm_wiki.hooks import hooks_installed, install_hooks, run_hook, uninstall_hooks
from llm_wiki.pages import new_page


def _settings(p: Path) -> Path:
    return p / ".claude" / "settings.json"


def test_install_creates_both_hooks(tmp_path: Path):
    install_hooks(tmp_path)
    data = json.loads(_settings(tmp_path).read_text())
    assert "PreToolUse" in data["hooks"]
    assert "PostToolUse" in data["hooks"]
    assert hooks_installed(tmp_path)


def test_install_is_idempotent(tmp_path: Path):
    install_hooks(tmp_path)
    first = _settings(tmp_path).read_text()
    install_hooks(tmp_path)
    assert _settings(tmp_path).read_text() == first


def test_uninstall_restores_preexisting_settings(tmp_path: Path):
    _settings(tmp_path).parent.mkdir(parents=True)
    original = {"permissions": {"allow": ["Bash"]}}
    _settings(tmp_path).write_text(json.dumps(original, indent=2) + "\n")
    install_hooks(tmp_path)
    assert hooks_installed(tmp_path)
    uninstall_hooks(tmp_path)
    assert json.loads(_settings(tmp_path).read_text()) == original
    assert not hooks_installed(tmp_path)


def test_run_hook_pre_edit_blocks_protected(wiki_cfg: WikiConfig):
    payload = json.dumps({"tool_input": {"file_path": str(wiki_cfg.index_file)}})
    code, msg = run_hook("pre-edit", payload)
    assert code == 2
    assert "index.md" in msg


def test_run_hook_pre_edit_allows_pages(wiki_cfg: WikiConfig):
    p = new_page(wiki_cfg, type="note", title="Free")
    payload = json.dumps({"tool_input": {"file_path": str(p)}})
    assert run_hook("pre-edit", payload) == (0, "")


def test_run_hook_post_edit_rebuilds_index(wiki_cfg: WikiConfig):
    p = new_page(wiki_cfg, type="note", title="Fresh")
    assert not index_is_current(wiki_cfg)
    payload = json.dumps({"tool_input": {"file_path": str(p)}})
    code, _msg = run_hook("post-edit", payload)
    assert code == 0
    assert index_is_current(wiki_cfg)  # the hook rebuilt it


def test_run_hook_ignores_junk(wiki_cfg: WikiConfig):
    assert run_hook("pre-edit", "not json") == (0, "")
    assert run_hook("pre-edit", "") == (0, "")
    assert run_hook("post-edit", json.dumps({"tool_input": {}})) == (0, "")
