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
    Check if Python build supports free-threading (even if GIL is currently enabled).

    This detects if the Python interpreter was built with free-threading support,
    regardless of whether PYTHON_GIL=0 is set.

    Returns:
        True if Python supports free-threading, False otherwise.

    """
    # If _is_gil_enabled exists, this is a free-threading capable build
    if hasattr(sys, "_is_gil_enabled"):
        return True

    # Also check sysconfig
    try:
        import sysconfig

        return sysconfig.get_config_var("Py_GIL_DISABLED") is not None
    except ImportError, AttributeError:
        pass

    return False


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
    # If GIL is already disabled, no message needed
    if is_gil_disabled():
        return None

    # Check if this Python build supports free-threading
    if has_free_threading_support():
        # Python supports free-threading but GIL is enabled
        return (
            "GIL is enabled - parallel builds limited to process isolation",
            "Set PYTHON_GIL=0 before running for ~1.5-2x faster builds",
        )

    # Python doesn't support free-threading (standard build)
    # Suggest installing the free-threaded variant
    return (
        "Using standard Python build (GIL enabled)",
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
