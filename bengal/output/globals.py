"""Global CLI output instance management.

This module is the single owner of Bengal's process-wide :class:`CLIOutput`.
CLI-facing compatibility wrappers in ``bengal.cli.utils.output`` delegate here
so Milo commands, Kida rendering helpers, and older call sites cannot drift onto
different singleton instances.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.output.core import CLIOutput

_cli_output: CLIOutput | None = None
_cli_output_lock = threading.Lock()


def _new_cli_output(
    profile: Any | None = None,
    quiet: bool = False,
    verbose: bool = False,
) -> CLIOutput:
    from bengal.output.core import CLIOutput

    return CLIOutput(profile=profile, quiet=quiet, verbose=verbose)


def get_cli_output(
    quiet: bool = False,
    verbose: bool = False,
    profile: Any | None = None,
    use_global: bool = True,
) -> CLIOutput:
    """
    Get a CLI output instance.

    By default, returns the shared CLIOutput instance, creating a default
    instance when needed. Passing ``quiet``, ``verbose``, or ``profile`` updates
    the shared instance for the current command. Use ``use_global=False`` for an
    isolated renderer that does not affect process-global CLI state.

    Returns:
        The configured CLIOutput instance.

    """
    global _cli_output
    if not use_global:
        return _new_cli_output(profile=profile, quiet=quiet, verbose=verbose)

    if _cli_output is None:
        with _cli_output_lock:
            if _cli_output is None:
                _cli_output = _new_cli_output(profile=profile, quiet=quiet, verbose=verbose)
    elif quiet or verbose or profile is not None:
        with _cli_output_lock:
            _cli_output = _new_cli_output(profile=profile, quiet=quiet, verbose=verbose)
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
    with _cli_output_lock:
        _cli_output = _new_cli_output(profile=profile, quiet=quiet, verbose=verbose)
    return _cli_output


def reset_cli_output() -> None:
    """Reset the shared CLI output instance.

    This is primarily for tests that need deterministic stdout/stderr capture.
    """
    global _cli_output
    with _cli_output_lock:
        _cli_output = None
