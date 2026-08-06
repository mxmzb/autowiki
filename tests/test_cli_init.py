from pathlib import Path

from typer.testing import CliRunner

from autowiki.cli import app
from autowiki.config import load_config

runner = CliRunner()


def test_init_yes_defaults_to_alongside_pr(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    result = runner.invoke(
        app, ["init", str(project), "--target", "generic", "--yes"]
    )
    assert result.exit_code == 0, result.output
    assert load_config(project / "wiki").wiki_update_mode == "alongside_pr"


def test_init_explicit_mode_bypasses_prompt(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    result = runner.invoke(
        app,
        [
            "init",
            str(project),
            "--target",
            "generic",
            "--wiki-update-mode",
            "after-merge",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "How should agents handle wiki updates?" not in result.output
    assert load_config(project / "wiki").wiki_update_mode == "after_merge"


def test_init_interactive_second_choice_selects_after_merge(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    result = runner.invoke(
        app, ["init", str(project), "--target", "generic"], input="2\n"
    )
    assert result.exit_code == 0, result.output
    assert "How should agents handle wiki updates?" in result.output
    assert load_config(project / "wiki").wiki_update_mode == "after_merge"


def test_init_interactive_enter_defaults_to_alongside_pr(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    result = runner.invoke(
        app, ["init", str(project), "--target", "generic"], input="\n"
    )
    assert result.exit_code == 0, result.output
    assert load_config(project / "wiki").wiki_update_mode == "alongside_pr"


def test_init_invalid_mode_does_not_mutate_project(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    result = runner.invoke(
        app,
        [
            "init",
            str(project),
            "--target",
            "generic",
            "--wiki-update-mode",
            "sometimes",
        ],
    )
    assert result.exit_code != 0
    assert "alongside_pr" in result.output
    assert "after_merge" in result.output
    assert not (project / "wiki").exists()


def test_reinit_without_option_preserves_mode_without_prompt(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    first = runner.invoke(
        app,
        [
            "init",
            str(project),
            "--target",
            "generic",
            "--wiki-update-mode",
            "after-merge",
        ],
    )
    assert first.exit_code == 0, first.output

    result = runner.invoke(app, ["init", str(project), "--target", "generic"])
    assert result.exit_code == 0, result.output
    assert "How should agents handle wiki updates?" not in result.output
    assert load_config(project / "wiki").wiki_update_mode == "after_merge"


def test_reinit_explicit_mode_updates_existing_install(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    first = runner.invoke(
        app,
        [
            "init",
            str(project),
            "--target",
            "generic",
            "--wiki-update-mode",
            "after-merge",
        ],
    )
    assert first.exit_code == 0, first.output

    result = runner.invoke(
        app,
        [
            "init",
            str(project),
            "--target",
            "generic",
            "--wiki-update-mode",
            "alongside-pr",
        ],
    )
    assert result.exit_code == 0, result.output
    assert load_config(project / "wiki").wiki_update_mode == "alongside_pr"
    assert "create a draft PR" in (project / "AGENTS.md").read_text()
