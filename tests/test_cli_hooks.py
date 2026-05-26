import json
from pathlib import Path

from typer.testing import CliRunner

from llm_wiki.cli import app
from llm_wiki.hooks import hooks_installed

runner = CliRunner()


def test_init_with_hooks_installs(tmp_path: Path):
    proj = tmp_path / "p"
    proj.mkdir()
    r = runner.invoke(app, ["init", str(proj), "--target", "claude", "--hooks"])
    assert r.exit_code == 0
    assert (proj / ".claude" / "settings.json").exists()
    assert hooks_installed(proj)


def test_hook_pre_edit_blocks_protected(tmp_path: Path):
    proj = tmp_path / "p"
    proj.mkdir()
    runner.invoke(app, ["init", str(proj), "--target", "generic"])
    wiki = proj / "wiki"
    payload = json.dumps({"tool_input": {"file_path": str(wiki / "index.md")}})
    r = runner.invoke(app, ["hook", "pre-edit"], input=payload)
    assert r.exit_code == 2


def test_install_then_uninstall_hooks(tmp_path: Path):
    proj = tmp_path / "p"
    proj.mkdir()
    runner.invoke(app, ["init", str(proj), "--target", "claude"])
    wiki = proj / "wiki"
    assert runner.invoke(app, ["install-hooks", "--wiki", str(wiki)]).exit_code == 0
    assert hooks_installed(proj)
    assert runner.invoke(app, ["uninstall-hooks", "--wiki", str(wiki)]).exit_code == 0
    assert not hooks_installed(proj)
