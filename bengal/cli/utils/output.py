"""
Unified CLI output management.

Provides a single source of truth for CLIOutput instances, consolidating
the previously split functionality from output/globals.py and helpers/cli_output.py.

Functions:
    get_cli_output: Get or create a CLIOutput instance
    init_cli_output: Initialize the global CLIOutput with custom settings
    reset_cli_output: Reset the global instance (useful for testing)

The module maintains a singleton pattern for commands that share output state,
while also supporting factory-style creation for isolated instances.

Example:
    # Get global instance (creates if needed)
    cli = get_cli_output()

    # Get with quiet/verbose flags (updates global)
    cli = get_cli_output(quiet=True)

    # Create isolated instance (not global)
    cli = get_cli_output(use_global=False, quiet=True)

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.output import CLIOutput

_cli_output: CLIOutput | None = None


def get_cli_output(
    quiet: bool = False,
    verbose: bool = False,
    profile: Any | None = None,
    use_global: bool = True,
) -> CLIOutput:
    """
    Get or create a CLIOutput instance.

    By default, returns and updates the global singleton. Use `use_global=False`
    to create an isolated instance that won't affect the global state.

    Args:
        quiet: Suppress non-critical output
        verbose: Show detailed output
        profile: Build profile (Writer, Theme-Dev, Developer)
        use_global: If True, use/update the global singleton. If False, create
            a new isolated instance.

    Returns:
        CLIOutput instance configured with the specified parameters.

    Example:
        # Standard usage - gets/creates global instance
        cli = get_cli_output()

        # With flags - updates global instance
        cli = get_cli_output(quiet=True, verbose=False)

        # Isolated instance - doesn't affect global
        cli = get_cli_output(use_global=False, quiet=True)

    """
    global _cli_output

    from bengal.output import CLIOutput

    if use_global:
        # Create or update global instance
        if _cli_output is None or quiet or verbose or profile:
            # Create new instance if none exists or if flags are provided
            _cli_output = CLIOutput(profile=profile, quiet=quiet, verbose=verbose)
        return _cli_output
    else:
        # Create isolated instance
        return CLIOutput(profile=profile, quiet=quiet, verbose=verbose)


def init_cli_output(
    profile: Any | None = None,
    quiet: bool = False,
    verbose: bool = False,
) -> CLIOutput:
    """
    Initialize the global CLI output instance with custom settings.

    Should be called early in CLI startup to configure output behavior
    for the current command execution. This always creates a new global
    instance, replacing any existing one.

    Args:
        profile: Build profile (Writer, Theme-Dev, Developer)
        quiet: Suppress non-critical output
        verbose: Show detailed output

    Returns:
        The newly initialized CLIOutput instance.

    Example:
        # At start of command
        cli = init_cli_output(profile=BuildProfile.DEVELOPER, verbose=True)

    """
    global _cli_output

    from bengal.output import CLIOutput

    _cli_output = CLIOutput(profile=profile, quiet=quiet, verbose=verbose)
    return _cli_output


def reset_cli_output() -> None:
    """
    Reset the global CLIOutput instance.

    Primarily useful for testing to ensure clean state between tests.
    """
    global _cli_output
    _cli_output = None
