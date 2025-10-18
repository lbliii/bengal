from click.testing import CliRunner

from bengal.cli import main


def test_cli_help_runs():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])  # ensure no circular imports and help renders
    assert result.exit_code == 0
    assert "Usage:" in result.output
