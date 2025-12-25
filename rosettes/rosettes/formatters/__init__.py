"""Rosettes formatters package.

Provides HTML and Terminal formatters for syntax highlighting output.
All formatters are lazy-loaded for fast import times.

Formatters:
    - HtmlFormatter: Generate HTML with CSS classes
    - TerminalFormatter: Generate ANSI-colored terminal output
"""

from __future__ import annotations

__all__ = ["HtmlFormatter", "TerminalFormatter"]

# Lazy loading cache
_cache: dict[str, type] = {}


def __getattr__(name: str) -> type:
    """Lazy-load formatters on first access."""
    if name == "HtmlFormatter":
        if "HtmlFormatter" not in _cache:
            from rosettes.formatters.html import HtmlFormatter

            _cache["HtmlFormatter"] = HtmlFormatter
        return _cache["HtmlFormatter"]

    if name == "TerminalFormatter":
        if "TerminalFormatter" not in _cache:
            from rosettes.formatters.terminal import TerminalFormatter

            _cache["TerminalFormatter"] = TerminalFormatter
        return _cache["TerminalFormatter"]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes for tab completion."""
    return list(__all__)
