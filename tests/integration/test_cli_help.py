"""Integration test for CLI help output.

Uses Phase 1 infrastructure: run_cli() helper.
"""

from tests._testing.cli import run_cli


def test_cli_help_runs():
    """Test CLI help runs without circular imports and renders properly."""
    result = run_cli(["--help"])
    result.assert_ok()
    assert "bengal" in result.stdout


def test_build_and_serve_help_do_not_expose_dashboard_flags():
    """Dashboard UI flags were removed with the Textual runtime."""
    build_result = run_cli(["build", "--help"])
    serve_result = run_cli(["serve", "--help"])

    build_result.assert_ok()
    serve_result.assert_ok()
    assert "--dashboard" not in build_result.stdout
    assert "--dashboard" not in serve_result.stdout
