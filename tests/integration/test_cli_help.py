"""Integration test for CLI help output.

Uses Phase 1 infrastructure: run_cli() helper.
"""

from tests._testing.cli import run_cli


def test_cli_help_runs():
    """Test CLI help runs without circular imports and renders properly."""
    result = run_cli(["--help"])
    result.assert_ok()
    assert "Usage:" in result.stdout
