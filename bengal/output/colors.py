"""
Color utilities for CLI output.

Provides ANSI and Rich color codes for HTTP status codes and methods.
"""

from __future__ import annotations


def get_status_color_code(status: str) -> str:
    """Get ANSI color code for HTTP status code."""
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
    """Get ANSI color code for HTTP method."""
    colors = {
        "GET": "\033[36m",  # Cyan
        "POST": "\033[33m",  # Yellow
        "PUT": "\033[35m",  # Magenta
        "DELETE": "\033[31m",  # Red
        "PATCH": "\033[35m",  # Magenta
    }
    return colors.get(method, "\033[37m")  # Default white


def get_status_style(status: str) -> str:
    """Get Rich style name for HTTP status code."""
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
    """Get Rich style name for HTTP method."""
    styles = {
        "GET": "cyan",
        "POST": "yellow",
        "PUT": "magenta",
        "DELETE": "red",
        "PATCH": "magenta",
    }
    return styles.get(method, "default")
