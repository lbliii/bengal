"""
Global CLI output instance management.

This module manages a singleton CLIOutput instance for consistent
output formatting across all CLI commands. The global instance can
be initialized with profile-specific settings.

Functions:
    get_cli_output: Get the global CLIOutput instance (creates if needed)
    init_cli_output: Initialize global instance with custom settings

Note:
    The global instance pattern is used here to allow commands to share
    a single output configuration without passing it through every function.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.cli.output.core import CLIOutput

_cli_output: CLIOutput | None = None


def get_cli_output() -> CLIOutput:
    """
    Get the global CLI output instance.

    Creates a default CLIOutput instance if one hasn't been initialized.
    Use init_cli_output() first if you need custom settings.

    Returns:
        The global CLIOutput instance.
    """
    global _cli_output
    if _cli_output is None:
        from bengal.cli.output.core import CLIOutput

        _cli_output = CLIOutput()
    return _cli_output


def init_cli_output(
    profile: Any | None = None, quiet: bool = False, verbose: bool = False
) -> CLIOutput:
    """
    Initialize the global CLI output instance with custom settings.

    Should be called early in CLI startup to configure output behavior
    for the current command execution.

    Args:
        profile: Build profile (Writer, Theme-Dev, Developer)
        quiet: Suppress non-critical output
        verbose: Show detailed output

    Returns:
        The newly initialized CLIOutput instance.
    """
    global _cli_output
    from bengal.cli.output.core import CLIOutput

    _cli_output = CLIOutput(profile=profile, quiet=quiet, verbose=verbose)
    return _cli_output
