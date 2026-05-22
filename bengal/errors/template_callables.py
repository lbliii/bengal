"""Template callable scanning used by error suggestions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_KNOWN_SAFE_CALLABLES: frozenset[str] = frozenset(
    {
        "range",
        "len",
        "dict",
        "list",
        "str",
        "int",
        "float",
        "bool",
        "set",
        "tuple",
        "enumerate",
        "zip",
        "sorted",
        "reversed",
        "min",
        "max",
        "sum",
        "abs",
        "round",
        "type",
        "isinstance",
        "getattr",
        "hasattr",
        "callable",
        "print",
        "super",
        "loop",
        "self",
        "caller",
        "if",
        "else",
        "elif",
        "for",
        "endfor",
        "endif",
        "block",
        "endblock",
        "macro",
        "endmacro",
        "call",
        "endcall",
        "include",
        "import",
        "from",
        "extends",
        "with",
        "endwith",
    }
)

_FUNC_CALL_PATTERN = re.compile(r"\{\{[^}]*\b(\w+)\s*\([^}]*\}\}")
_FILTER_PATTERN = re.compile(r"\|\s*(\w+)")


def scan_template_for_callables(template_path: Path) -> list[str]:
    """Return likely-None callable suspects from a template file."""
    try:
        with open(template_path, encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        return []

    suspects: list[str] = []

    for match in _FUNC_CALL_PATTERN.finditer(content):
        func_name = match.group(1)
        if func_name.lower() not in _KNOWN_SAFE_CALLABLES:
            suspects.append(f"function '{func_name}'")

    for match in _FILTER_PATTERN.finditer(content):
        filter_name = match.group(1)
        if filter_name.lower() not in _KNOWN_SAFE_CALLABLES:
            suspects.append(f"filter '{filter_name}'")

    return suspects


__all__ = ["scan_template_for_callables"]
