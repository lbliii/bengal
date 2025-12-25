"""Rosettes formatters package.

Provides HTML and Terminal formatters for syntax highlighting output.

Formatters:
    - HtmlFormatter: Generate HTML with CSS classes
    - TerminalFormatter: Generate ANSI-colored terminal output
"""

from rosettes.formatters.html import HtmlFormatter
from rosettes.formatters.terminal import TerminalFormatter

__all__ = ["HtmlFormatter", "TerminalFormatter"]
