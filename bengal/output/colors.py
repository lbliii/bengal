"""
Color utilities for CLI output.

Provides ANSI escape codes and Rich style names for HTTP status codes
and request methods. Used by the dev server output for colorized
request logging.

Color Mapping:
    Status codes are colorized by category:
    - 2xx Success: Green
    - 304 Not Modified: Gray (dimmed)
    - 3xx Redirect: Cyan
    - 4xx Client Error: Yellow
    - 5xx Server Error: Red

    HTTP methods are colorized by semantic meaning:
    - GET: Cyan (read operation)
    - POST: Yellow (create operation)
    - PUT/PATCH: Magenta (update operation)
    - DELETE: Red (destructive operation)

Related:
    - bengal/output/dev_server.py: Consumes these color functions
    - bengal/utils/rich_console.py: Rich console configuration
"""

from __future__ import annotations


def get_status_color_code(status: str) -> str:
    """
    Get ANSI escape sequence for HTTP status code colorization.

    Maps HTTP status codes to ANSI color codes for terminal output
    when Rich is not available.

    Args:
        status: HTTP status code as string (e.g., "200", "404")

    Returns:
        ANSI escape sequence for the appropriate color, or empty
        string if status cannot be parsed.

    Example:
        >>> code = get_status_color_code("200")
        >>> print(f"{code}200\\033[0m")  # Green "200"
    """
    try:
        code = int(status)
        if 200 <= code < 300:
            return "\033[32m"  # Green
        elif code == 304:
            return "\033[90m"  # Gray
        elif 300 <= code < 400:
            return "\033[36m"  # Cyan
        elif 400 <= code < 500:
            return "\033[33m"  # Yellow
        else:
            return "\033[31m"  # Red
    except (ValueError, TypeError):
        return ""


def get_method_color_code(method: str) -> str:
    """
    Get ANSI escape sequence for HTTP method colorization.

    Maps HTTP methods to ANSI color codes for terminal output
    when Rich is not available.

    Args:
        method: HTTP method name (e.g., "GET", "POST")

    Returns:
        ANSI escape sequence for the appropriate color.

    Example:
        >>> code = get_method_color_code("GET")
        >>> print(f"{code}GET\\033[0m")  # Cyan "GET"
    """
    colors = {
        "GET": "\033[36m",  # Cyan
        "POST": "\033[33m",  # Yellow
        "PUT": "\033[35m",  # Magenta
        "DELETE": "\033[31m",  # Red
        "PATCH": "\033[35m",  # Magenta
    }
    return colors.get(method, "\033[37m")  # Default white


def get_status_style(status: str) -> str:
    """
    Get Rich style name for HTTP status code.

    Maps HTTP status codes to Rich markup style names for
    colorized console output.

    Args:
        status: HTTP status code as string (e.g., "200", "404")

    Returns:
        Rich style name (e.g., "green", "red", "dim").

    Example:
        >>> style = get_status_style("404")
        >>> console.print(f"[{style}]404[/{style}]")
    """
    try:
        code = int(status)
        if 200 <= code < 300:
            return "green"
        elif code == 304:
            return "dim"
        elif 300 <= code < 400:
            return "cyan"
        elif 400 <= code < 500:
            return "yellow"
        else:
            return "red"
    except (ValueError, TypeError):
        return "default"


def get_method_style(method: str) -> str:
    """
    Get Rich style name for HTTP method.

    Maps HTTP methods to Rich markup style names for
    colorized console output.

    Args:
        method: HTTP method name (e.g., "GET", "POST")

    Returns:
        Rich style name (e.g., "cyan", "yellow").

    Example:
        >>> style = get_method_style("POST")
        >>> console.print(f"[{style}]POST[/{style}]")
    """
    styles = {
        "GET": "cyan",
        "POST": "yellow",
        "PUT": "magenta",
        "DELETE": "red",
        "PATCH": "magenta",
    }
    return styles.get(method, "default")
