"""
GIL (Global Interpreter Lock) detection utilities.

Provides functions to detect if Python is running with the GIL disabled
(free-threaded mode) and generate helpful messages for users.

Python 3.13+ introduced experimental support for disabling the GIL via
the PYTHON_GIL=0 environment variable when using the free-threaded build
(python3.13t or python3.14t). This enables true parallelism in
ThreadPoolExecutor.

See Also:
- PEP 703: Making the Global Interpreter Lock Optional
- https://docs.python.org/3/using/configure.html#cmdoption-disable-gil

"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import StrEnum


class FreeThreadingState(StrEnum):
    """How the current interpreter relates to Bengal's free-threading model."""

    ACTIVE = "active"
    GIL_ENABLED = "gil_enabled"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class FreeThreadingStatus:
    """User-facing summary of free-threading readiness."""

    state: FreeThreadingState
    python_version: str
    headline: str
    body_lines: tuple[str, ...]
    fix_lines: tuple[str, ...]


def _python_version_line() -> str:
    return sys.version.split("\n", 1)[0].strip()


def is_free_threading_build() -> bool:
    """
    Return True when this interpreter is a free-threading build (``3.14t``).

    Standard ``3.14.x`` builds expose ``sys._is_gil_enabled()`` but cannot
    disable the GIL at runtime — the version string is the reliable signal.
    """
    return "free-threading" in sys.version.lower()


def is_gil_disabled() -> bool:
    """
    Check if running on free-threaded Python (GIL disabled).

    Python 3.13t+ with PYTHON_GIL=0 can disable the GIL, making threads
    truly parallel. This enables significant performance improvements
    for CPU-bound parallel workloads like page rendering.

    Returns:
        True if running on free-threaded Python with GIL disabled,
        False otherwise (including older Python versions).

    Example:
            >>> if is_gil_disabled():
            ...     print("True parallelism enabled!")
            ... else:
            ...     print("GIL is enabled - consider using free-threaded Python")

    """
    # Check if sys._is_gil_enabled() exists and returns False
    if hasattr(sys, "_is_gil_enabled"):
        try:
            return not sys._is_gil_enabled()
        except AttributeError, TypeError:
            pass

    # Fallback: check sysconfig for Py_GIL_DISABLED
    try:
        import sysconfig

        return sysconfig.get_config_var("Py_GIL_DISABLED") == 1
    except ImportError, AttributeError:
        pass

    return False


def has_free_threading_support() -> bool:
    """
    Check if this interpreter is a free-threading build.

    Returns:
        True only for ``python3.13t`` / ``python3.14t`` style builds.
        Standard ``3.14.x`` builds return False even though they expose
        ``sys._is_gil_enabled()``.

    """
    return is_free_threading_build()


def get_free_threading_status() -> FreeThreadingStatus:
    """
    Describe how the current interpreter relates to Bengal's performance model.

    Returns:
        FreeThreadingStatus with plain-language guidance for the CLI gate.
    """
    version = _python_version_line()

    if is_gil_disabled():
        return FreeThreadingStatus(
            state=FreeThreadingState.ACTIVE,
            python_version=version,
            headline="Free-threading is active",
            body_lines=(),
            fix_lines=(),
        )

    if is_free_threading_build():
        return FreeThreadingStatus(
            state=FreeThreadingState.GIL_ENABLED,
            python_version=version,
            headline="Free-threading Python detected, but the GIL is still on",
            body_lines=(
                "Bengal parallel builds cannot use all of your CPU cores until the GIL is disabled.",
                "Expect noticeably slower builds and dev-server reloads (often 1.5–2× or more).",
            ),
            fix_lines=(
                "Restart with the GIL disabled, for example:",
                "  PYTHON_GIL=0 bengal serve",
                "  PYTHON_GIL=0 bengal build",
            ),
        )

    return FreeThreadingStatus(
        state=FreeThreadingState.UNSUPPORTED,
        python_version=version,
        headline="You are not running Bengal on free-threading Python",
        body_lines=(
            "This interpreter is a standard Python build with the GIL enabled.",
            "Bengal is designed around free-threaded Python 3.13t/3.14t for parallel builds.",
            "Without it, builds and live reloads are often much slower (1.5–2× or more).",
        ),
        fix_lines=(
            "Install a free-threading build (python3.14t), recreate your environment, then run:",
            "  uv venv --python python3.14t && uv sync",
            "  PYTHON_GIL=0 bengal serve",
        ),
    )


def get_gil_status_message() -> tuple[str, str] | None:
    """
    Get a user-friendly message about GIL status for performance tips.

    Returns:
        A tuple of (message, tip) if GIL is enabled and could be disabled,
        or None if GIL is already disabled or free-threading isn't available.

        The message describes the current state, and the tip shows how to
        enable free-threading for better performance.

    Example:
            >>> result = get_gil_status_message()
            >>> if result:
            ...     message, tip = result
            ...     print(f"{message}")
            ...     print(f"Tip: {tip}")

    """
    status = get_free_threading_status()
    if status.state is FreeThreadingState.ACTIVE:
        return None

    if status.state is FreeThreadingState.GIL_ENABLED:
        return (
            status.headline,
            "Set PYTHON_GIL=0 before running for ~1.5-2x faster builds",
        )

    return (
        status.headline,
        "Install Python 3.13t+ (free-threaded) for ~1.5-2x faster builds",
    )


def format_gil_tip_for_cli() -> str | None:
    """
    Format a CLI-friendly tip about GIL status.

    Returns a single-line tip suitable for display with cli.tip(),
    or None if no tip is needed.

    Example:
            >>> tip = format_gil_tip_for_cli()
            >>> if tip:
            ...     cli.tip(tip)

    """
    result = get_gil_status_message()
    if result is None:
        return None

    _, tip = result
    return tip
