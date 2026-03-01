"""
Shared utilities for CLI output system.

Centralizes ANSI escape codes, color mappings, and helper functions
used across the output package. This module provides a single source
of truth for terminal formatting constants.

Features:
- ANSI escape code constants for terminal coloring
- Unified HTTP status code → color mappings
- Unified HTTP method → color mappings
- Helper functions for color lookups

Related:
- bengal/output/colors.py: Uses mappings for status/method colorization
- bengal/output/dev_server.py: Uses ANSI constants for fallback output

"""

from __future__ import annotations


class ANSI:
    """
    ANSI escape codes for terminal coloring.

    Provides named constants for common ANSI escape sequences used
    in plain-text terminal output when Rich is not available.

    Usage:
        >>> print(f"{ANSI.GREEN}Success{ANSI.RESET}")

    """

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[90m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    WHITE = "\033[37m"


# Unified color mapping: (rich_style, ansi_code)
# Single source of truth for HTTP status code colorization
STATUS_COLORS: dict[str, tuple[str, str]] = {
    "2xx": ("green", ANSI.GREEN),
    "304": ("dim", ANSI.DIM),
    "3xx": ("cyan", ANSI.CYAN),
    "4xx": ("yellow", ANSI.YELLOW),
    "5xx": ("red", ANSI.RED),
}

# Unified color mapping for HTTP methods
METHOD_COLORS: dict[str, tuple[str, str]] = {
    "GET": ("cyan", ANSI.CYAN),
    "POST": ("yellow", ANSI.YELLOW),
    "PUT": ("magenta", ANSI.MAGENTA),
    "DELETE": ("red", ANSI.RED),
    "PATCH": ("magenta", ANSI.MAGENTA),
}

# Default colors when lookup fails
DEFAULT_STYLE = "default"
DEFAULT_ANSI = ANSI.WHITE


def get_status_category(status: str) -> str:
    """
    Convert HTTP status code to category key for color lookup.

    Args:
        status: HTTP status code as string (e.g., "200", "404")

    Returns:
        Category key (e.g., "2xx", "304", "4xx") or "default" if
        the status cannot be parsed.

    Example:
        >>> get_status_category("200")
        '2xx'
        >>> get_status_category("304")
        '304'
        >>> get_status_category("invalid")
        'default'

    """
    try:
        code = int(status)
        if code == 304:
            return "304"
        category = code // 100
        if 2 <= category <= 5:
            return f"{category}xx"
        return "default"
    except ValueError, TypeError:
        return "default"


def get_status_style(status: str) -> str:
    """
    Get Rich style name for HTTP status code.

    Args:
        status: HTTP status code as string (e.g., "200", "404")

    Returns:
        Rich style name (e.g., "green", "red", "dim").

    Example:
        >>> get_status_style("404")
        'yellow'

    """
    category = get_status_category(status)
    return STATUS_COLORS.get(category, (DEFAULT_STYLE, ""))[0]


def get_status_ansi(status: str) -> str:
    """
    Get ANSI escape code for HTTP status code.

    Args:
        status: HTTP status code as string (e.g., "200", "404")

    Returns:
        ANSI escape sequence for the appropriate color.

    Example:
        >>> code = get_status_ansi("200")
        >>> print(f"{code}200{ANSI.RESET}")  # Green "200"

    """
    category = get_status_category(status)
    return STATUS_COLORS.get(category, ("", ""))[1]


def get_method_style(method: str) -> str:
    """
    Get Rich style name for HTTP method.

    Args:
        method: HTTP method name (e.g., "GET", "POST")

    Returns:
        Rich style name (e.g., "cyan", "yellow").

    Example:
        >>> get_method_style("POST")
        'yellow'

    """
    return METHOD_COLORS.get(method, (DEFAULT_STYLE, ""))[0]


def get_method_ansi(method: str) -> str:
    """
    Get ANSI escape code for HTTP method.

    Args:
        method: HTTP method name (e.g., "GET", "POST")

    Returns:
        ANSI escape sequence for the appropriate color.

    Example:
        >>> code = get_method_ansi("GET")
        >>> print(f"{code}GET{ANSI.RESET}")  # Cyan "GET"

    """
    return METHOD_COLORS.get(method, ("", DEFAULT_ANSI))[1]
