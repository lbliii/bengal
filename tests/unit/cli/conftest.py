"""Shared fixtures for CLI tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_cli_output():
    """Reset the global CLIOutput singleton between tests.

    CLIOutput uses a module-level global singleton. Without resetting,
    a previous test's instance writes to a stale stdout reference,
    causing subsequent tests to see empty CliRunner output.
    """
    from bengal.cli.utils.output import reset_cli_output

    reset_cli_output()
    yield
    reset_cli_output()
