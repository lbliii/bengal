"""
Code-related utilities for syntax highlighting and code block processing.

Provides canonical implementations for code fence parsing, line highlight
specifications, and related text processing. These utilities consolidate
duplicate implementations found in rendering and parsing modules.

Example:

```python
from bengal.utils.primitives.code import parse_hl_lines, parse_code_info

lines = parse_hl_lines("1,3-5,7")  # [1, 3, 4, 5, 7]
lang, highlights = parse_code_info("python {1,3-5}")  # ("python", [1, 3, 4, 5])
```
"""

from __future__ import annotations

import re

# Pattern to parse code fence info with optional line highlights
# Matches: python, python {1,3}, python {1-3,5}
HL_LINES_PATTERN = re.compile(r"^(\S+)\s*(?:\{([^}]+)\})?$")


def parse_hl_lines(hl_spec: str) -> list[int]:
    """
    Parse line highlight specification into list of line numbers.

    Consolidates implementations from:
    - bengal/parsing/backends/patitas/renderers/blocks.py (_parse_hl_lines)
    - bengal/rendering/highlighting/deferred.py (parse_hl_lines)
    - bengal/parsing/backends/patitas/directives/builtins/code_tabs.py (parse_hl_lines)

    Supports:
    - Single line: "5" -> [5]
    - Multiple lines: "1,3,5" -> [1, 3, 5]
    - Ranges: "1-3" -> [1, 2, 3]
    - Mixed: "1,3-5,7" -> [1, 3, 4, 5, 7]

    Args:
        hl_spec: Line specification string (e.g., "1,3-5,7")

    Returns:
        Sorted list of unique line numbers

    Examples:
        >>> parse_hl_lines("5")
        [5]
        >>> parse_hl_lines("1,3,5")
        [1, 3, 5]
        >>> parse_hl_lines("1-3")
        [1, 2, 3]
        >>> parse_hl_lines("1,3-5,7")
        [1, 3, 4, 5, 7]
        >>> parse_hl_lines("")
        []
        >>> parse_hl_lines("invalid")
        []

    """
    if not hl_spec:
        return []

    lines: set[int] = set()
    for part in hl_spec.split(","):
        part = part.strip()
        if "-" in part:
            # Range: "3-5" -> 3, 4, 5
            try:
                start, end = part.split("-", 1)
                lines.update(range(int(start), int(end) + 1))
            except ValueError:
                continue
        else:
            # Single line
            try:
                lines.add(int(part))
            except ValueError:
                continue
    return sorted(lines)


def parse_code_info(info: str) -> tuple[str, list[int]]:
    """
    Parse code fence info string for language and line highlights.

    Handles common code fence formats like:
    - "python" -> ("python", [])
    - "python {1,3-5}" -> ("python", [1, 3, 4, 5])
    - "javascript {2}" -> ("javascript", [2])

    Args:
        info: Code fence info string (e.g., "python {1,3-5}")

    Returns:
        Tuple of (language, hl_lines list)

    Examples:
        >>> parse_code_info("python")
        ('python', [])
        >>> parse_code_info("python {1,3}")
        ('python', [1, 3])
        >>> parse_code_info("")
        ('', [])

    """
    if not info:
        return "", []

    info = info.strip()
    match = HL_LINES_PATTERN.match(info)
    if match:
        lang = match.group(1)
        hl_spec = match.group(2)
        return lang, parse_hl_lines(hl_spec) if hl_spec else []

    # Fallback: treat entire string as language
    return info, []
