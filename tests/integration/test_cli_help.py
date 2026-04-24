"""Integration test for CLI help and version output.

Subprocess-level smoke: pairs with ``tests/unit/cli/test_milo_parser_construction.py``.
The unit test catches parser-build conflicts fast; this one catches entry-point,
console_scripts, and subprocess-level regressions.
"""

from tests._testing.cli import run_cli


def test_cli_help_runs():
    """Test CLI help runs without circular imports and renders properly."""
    result = run_cli(["--help"])
    result.assert_ok()
    assert "bengal" in result.stdout


def test_cli_version_runs():
    """Test ``bengal --version`` exits 0 and prints the current version.

    Regression guard for v0.3.1, where argparse conflict crashed every invocation
    — including ``--version`` — before user code ran.
    """
    result = run_cli(["--version"])
    result.assert_ok()
    assert any(ch.isdigit() for ch in result.stdout), (
        f"Expected version digits in stdout, got: {result.stdout!r}"
    )
