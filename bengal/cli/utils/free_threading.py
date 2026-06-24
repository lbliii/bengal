"""Free-threading readiness gate for build and serve commands."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from bengal.utils.concurrency.gil import (
    FreeThreadingState,
    FreeThreadingStatus,
    get_free_threading_status,
)

if TYPE_CHECKING:
    from bengal.output.core import CLIOutput


def free_threading_bypassed(*, yes: bool = False) -> bool:
    """Return True when the user explicitly opted out of the gate."""
    if yes:
        return True
    return os.environ.get("BENGAL_ALLOW_GIL", "").lower() in {"1", "true", "yes"}


def ensure_free_threading_or_confirm(
    cli: CLIOutput,
    *,
    command: str,
    yes: bool = False,
) -> None:
    """
    Block build/serve when free-threading is unavailable unless the user confirms.

    Raises:
        SystemExit: When the user declines or non-interactive use needs --yes.
    """
    status = get_free_threading_status()
    if status.state is FreeThreadingState.ACTIVE:
        return

    if free_threading_bypassed(yes=yes):
        return

    _print_free_threading_warning(cli, status, command=command)

    if not sys.stdin.isatty():
        cli.error("Cannot continue without free-threading in non-interactive mode.")
        cli.tip("Use --yes to proceed anyway, or set BENGAL_ALLOW_GIL=1 for CI/scripts.")
        raise SystemExit(2)

    if not cli.confirm("Continue without free-threading?", default=False):
        cli.warning("Aborted — switch to free-threading Python, then try again.")
        raise SystemExit(130)


def _print_free_threading_warning(
    cli: CLIOutput,
    status: FreeThreadingStatus,
    *,
    command: str,
) -> None:
    cli.blank()
    cli.warning(status.headline)
    cli.detail(f"Command: bengal {command}", indent=1)
    cli.detail(f"Python: {status.python_version}", indent=1)
    for line in status.body_lines:
        cli.detail(line, indent=1)
    cli.blank()
    for line in status.fix_lines:
        cli.detail(line, indent=1)
    cli.blank()
