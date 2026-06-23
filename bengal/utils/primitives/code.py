"""
Code-related utilities for syntax highlighting and code block processing.

Provides canonical implementations for code fence parsing, line highlight
specifications, and related text processing. These utilities consolidate
duplicate implementations found in rendering and parsing modules.

Example:

```python
from bengal.utils.primitives.code import parse_fence_attrs, parse_hl_lines

lines = parse_hl_lines("1,3-5,7")  # [1, 3, 4, 5, 7]
attrs = parse_fence_attrs('python title="app.py" {1,3-5}')
```
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Pattern to parse code fence info with optional line highlights
# Matches: python, python {1,3}, python {1-3,5}, python {}
HL_LINES_PATTERN = re.compile(r"^(\S+)\s*(?:\{([^}]*)\})?$")

# Canonical fence info: language, optional diff flag, title, brace attrs, linenos
FENCE_INFO_PATTERN = re.compile(
    r"^(?P<lang>\S+)"
    r"(?:\s+(?P<diff>diff))?"
    r'(?:\s+title="(?P<title>[^"]*)")?'
    r"(?:\s*\{(?P<brace>[^}]*)\})?"
    r'(?:\s+title="(?P<title2>[^"]*)")?'
    r"(?:\s+(?P<linenos>linenos))?"
)

FRAME_PATTERN = re.compile(r"\bframe=(terminal|editor)\b")
COLLAPSE_PATTERN = re.compile(r"\bcollapse(?:=(open|closed))?\b")
ANNOTATE_PATTERN = re.compile(r'annotate="([^"]+)"')

# Shell-like languages get an implicit terminal frame unless frame= overrides.
TERMINAL_FRAME_LANGUAGES = frozenset(
    {"bash", "sh", "shell", "zsh", "console", "terminal", "powershell", "cmd", "pwsh"}
)


def default_frame_for_language(language: str) -> str | None:
    """Return the implicit premium frame for a fenced code language."""
    lang = language.lower()
    if not lang:
        return None
    if lang in TERMINAL_FRAME_LANGUAGES:
        return "terminal"
    return "editor"


@dataclass(frozen=True, slots=True)
class CodeFenceAttrs:
    """Parsed attributes from a markdown code fence info string."""

    language: str = ""
    hl_lines: tuple[int, ...] = ()
    title: str | None = None
    diff: bool = False
    show_linenos: bool = False
    frame: str | None = None
    collapsible: bool = False
    collapsed: bool = False
    annotations: tuple[tuple[int, str], ...] = ()

    @property
    def highlight_language(self) -> str:
        """Language passed to the highlighter (diff fences use the diff lexer)."""
        if self.diff or self.language.lower() == "diff":
            return "diff"
        return self.language


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
        if not part:
            continue
        if part.lower() == "diff":
            continue
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


def _parse_brace_content(brace: str | None) -> tuple[tuple[int, ...], bool]:
    """Parse brace content into highlight lines and optional diff flag."""
    if not brace:
        return (), False

    brace = brace.strip()
    if not brace:
        return (), False

    if brace.lower() == "diff":
        return (), True

    hl_lines = tuple(parse_hl_lines(brace))
    parts = {segment.strip().lower() for segment in brace.split(",") if segment.strip()}
    diff = "diff" in parts
    if diff:
        filtered = [
            segment.strip() for segment in brace.split(",") if segment.strip().lower() != "diff"
        ]
        hl_lines = tuple(line for segment in filtered for line in parse_hl_lines(segment))
    return hl_lines, diff


def parse_annotations(spec: str) -> tuple[tuple[int, str], ...]:
    """Parse ``1:Setup,3:Run`` annotation pairs from a fence annotate attribute."""
    if not spec.strip():
        return ()

    pairs: list[tuple[int, str]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        line_s, _, text = part.partition(":")
        try:
            line_no = int(line_s.strip())
        except ValueError:
            continue
        note = text.strip()
        if note:
            pairs.append((line_no, note))
    return tuple(pairs)


def _parse_optional_fence_flags(
    info: str,
) -> tuple[str | None, bool, bool, tuple[tuple[int, str], ...]]:
    frame_match = FRAME_PATTERN.search(info)
    frame = frame_match.group(1) if frame_match else None

    collapse_match = COLLAPSE_PATTERN.search(info)
    collapsible = collapse_match is not None
    collapsed = collapse_match is not None and collapse_match.group(1) == "closed"

    annotate_match = ANNOTATE_PATTERN.search(info)
    annotations = parse_annotations(annotate_match.group(1)) if annotate_match else ()

    return frame, collapsible, collapsed, annotations


def parse_fence_attrs(info: str) -> CodeFenceAttrs:
    """
    Parse a code fence info string into structured highlight attributes.

    Handles:
    - ``python`` -> language only
    - ``python {1,3-5}`` -> line highlights
    - ``python title="app.py" {2}`` -> title + highlights
    - ``python diff`` / ``diff`` -> unified diff rendering
    - ``python linenos`` -> line-number gutter (via rosettes)
    - ``bash frame=terminal collapse`` -> terminal chrome + collapsible region
    - ``python annotate="1:Setup,3:Run"`` -> inline per-line annotations
    - Non-shell languages get an implicit ``editor`` frame (shell gets ``terminal``)

    Args:
        info: Code fence info string after the opening backticks.

    Returns:
        Parsed :class:`CodeFenceAttrs`.
    """
    if not info:
        return CodeFenceAttrs()

    info = info.strip()
    frame, collapsible, collapsed, annotations = _parse_optional_fence_flags(info)
    show_linenos = bool(re.search(r"\blinenos\b", info))
    match = FENCE_INFO_PATTERN.match(info)
    if match:
        lang = match.group("lang")
        diff = match.group("diff") is not None or lang.lower() == "diff"
        title = match.group("title") or match.group("title2")
        if match.group("linenos") is not None:
            show_linenos = True
        hl_lines, brace_diff = _parse_brace_content(match.group("brace"))
        if frame is None:
            frame = default_frame_for_language(lang)
        return CodeFenceAttrs(
            language=lang,
            hl_lines=hl_lines,
            title=title or None,
            diff=diff or brace_diff,
            show_linenos=show_linenos,
            frame=frame,
            collapsible=collapsible,
            collapsed=collapsed,
            annotations=annotations,
        )

    # Fallback: first token is language, remainder ignored
    lang = info.split()[0]
    if frame is None:
        frame = default_frame_for_language(lang)
    return CodeFenceAttrs(
        language=lang,
        show_linenos=show_linenos,
        frame=frame,
        collapsible=collapsible,
        collapsed=collapsed,
        annotations=annotations,
    )


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
    attrs = parse_fence_attrs(info)
    return attrs.language, list(attrs.hl_lines)
