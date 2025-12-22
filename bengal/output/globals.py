"""
Global CLI output instance management.

Provides singleton-pattern access to a shared CLIOutput instance. This allows
CLI commands to share output configuration (profile, quiet/verbose modes)
without passing the instance through every function call.

Usage Pattern:
    CLI entry points call init_cli_output() once with configuration,
    then all subsystems call get_cli_output() to access the shared instance.

Note:
    While Bengal generally avoids global mutable state, this singleton pattern
    is acceptable for CLI-layer utilities where the alternative (threading
    context through every function) would add significant complexity.

Related:
    - bengal/output/core.py: CLIOutput class definition
    - bengal/cli/commands/: CLI commands that initialize and use global output
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.output.core import CLIOutput

_cli_output: CLIOutput | None = None


def get_cli_output() -> CLIOutput:
    """
    Get the global CLI output instance.

    Returns the shared CLIOutput instance, creating a default instance
    with no profile if one hasn't been initialized via init_cli_output().

    Returns:
        The global CLIOutput instance.

    Example:
        >>> cli = get_cli_output()
        >>> cli.success("Operation complete")
    """
    global _cli_output
    if _cli_output is None:
        from bengal.output.core import CLIOutput

        _cli_output = CLIOutput()
    return _cli_output


def init_cli_output(
    profile: Any | None = None, quiet: bool = False, verbose: bool = False
) -> CLIOutput:
    """
    Initialize the global CLI output instance with settings.

    Creates and stores a new CLIOutput instance with the specified
    configuration. Should be called early in CLI command execution
    to configure output before any messages are emitted.

    Args:
        profile: Build profile for profile-aware formatting (Writer, Theme-Dev,
            Developer). Controls which details are shown.
        quiet: If True, suppress non-critical output (INFO and below).
        verbose: If True, show detailed output including DEBUG messages.

    Returns:
        The newly initialized global CLIOutput instance.

    Example:
        >>> cli = init_cli_output(profile=BuildProfile.DEVELOPER, verbose=True)
        >>> cli.header("Starting build...")
    """
    global _cli_output
    from bengal.output.core import CLIOutput

    _cli_output = CLIOutput(profile=profile, quiet=quiet, verbose=verbose)
    return _cli_output
