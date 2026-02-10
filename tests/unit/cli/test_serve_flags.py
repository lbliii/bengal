"""Tests for serve command flag wiring."""

from click.testing import CliRunner

from bengal.cli import main


def test_serve_pipeline_flags_exist_in_help() -> None:
    """Serve help should expose lean/full pipeline toggle."""
    runner = CliRunner()
    result = runner.invoke(main, ["site", "serve", "--help"])

    assert result.exit_code == 0
    assert "--lean-pipeline" in result.output
    assert "--full-pipeline" in result.output


def test_serve_full_pipeline_flag_is_recognized() -> None:
    """The --full-pipeline flag should be accepted by click parsing."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["site", "serve", "--full-pipeline", "."])

    assert "No such option: --full-pipeline" not in result.output
