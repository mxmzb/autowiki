from typer.testing import CliRunner

from llm_wiki.cli import app

runner = CliRunner()


def test_version_prints_tool_and_schema_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "llm-wiki" in result.stdout
    assert "schema v" in result.stdout
