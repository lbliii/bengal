"""Marker detection utilities for list parsing.

Provides functions for detecting and classifying list markers.
"""

from __future__ import annotations

from bengal.rendering.parsers.patitas.parsing.blocks.list.types import ListMarkerInfo


def get_marker_indent(marker_value: str) -> int:
    """Extract indent level from list marker value.

    Marker values are prefixed with spaces by the lexer to encode indent.
    E.g., "  -" has indent 2, "1." has indent 0.

    Handles tabs by expanding them to the next multiple of 4 columns.

    Args:
        marker_value: The raw marker value from the token

    Returns:
        The column position where the marker starts
    """
    indent = 0
    for char in marker_value:
        if char == " ":
            indent += 1
        elif char == "\t":
            indent += 4 - (indent % 4)
        else:
            break
    return indent


def extract_marker_info(marker_value: str, start_indent: int | None = None) -> ListMarkerInfo:
    """Extract complete marker information from a marker token value.

    Args:
        marker_value: The raw marker value from the token
        start_indent: Override indent calculation (optional)

    Returns:
        ListMarkerInfo with all extracted information
    """
    indent = start_indent if start_indent is not None else get_marker_indent(marker_value)
    marker_stripped = marker_value.lstrip()
    ordered = marker_stripped[0].isdigit() if marker_stripped else False

    bullet_char = ""
    ordered_marker_char = ""
    start = 1

    if ordered:
        # Extract starting number and marker style from ordered list
        num_str = ""
        for c in marker_stripped:
            if c.isdigit():
                num_str += c
            else:
                ordered_marker_char = c
                break
        if num_str:
            start = int(num_str)
        marker_length = len(num_str) + 1  # digits + marker char
    else:
        bullet_char = marker_stripped[0] if marker_stripped else "-"
        marker_length = 1

    # Calculate actual marker length including trailing space
    if marker_stripped:
        marker_char_end = marker_length
        spaces_after_marker = 0
        for i in range(marker_char_end, len(marker_stripped)):
            if marker_stripped[i] == " ":
                spaces_after_marker += 1
            else:
                break
        marker_length = marker_char_end + spaces_after_marker

    return ListMarkerInfo(
        ordered=ordered,
        bullet_char=bullet_char,
        ordered_marker_char=ordered_marker_char,
        start=start,
        indent=indent,
        marker_length=marker_length,
    )


def is_list_marker(text: str) -> bool:
    """Check if text starts with a list marker pattern.

    Args:
        text: Text to check (should be stripped of leading whitespace)

    Returns:
        True if text starts with a valid list marker
    """
    if not text:
        return False

    first_char = text[0]

    # Unordered: -, *, + followed by space/tab or end of line
    if first_char in "-*+":
        return len(text) == 1 or (len(text) > 1 and text[1] in " \t")

    # Ordered: digits followed by . or ) and space/tab or end of line
    if first_char.isdigit():
        pos = 0
        while pos < len(text) and text[pos].isdigit():
            pos += 1
        if pos > 0 and pos < len(text) and text[pos] in ".)":
            return pos + 1 == len(text) or (pos + 1 < len(text) and text[pos + 1] in " \t")

    return False


def is_same_list_type(
    marker_value: str,
    ordered: bool,
    bullet_char: str,
    ordered_marker_char: str,
) -> bool:
    """Check if a marker belongs to the same list type.

    CommonMark requires same list type and marker character:
    - Unordered: -, *, + are different lists
    - Ordered: . and ) are different lists

    Args:
        marker_value: The raw marker value from the token
        ordered: Whether the current list is ordered
        bullet_char: Current list's bullet character (for unordered)
        ordered_marker_char: Current list's marker character (for ordered)

    Returns:
        True if the marker belongs to the same list
    """
    marker_stripped = marker_value.lstrip()
    if not marker_stripped:
        return False

    is_ordered = marker_stripped[0].isdigit()
    if is_ordered != ordered:
        return False

    if ordered:
        # Extract marker character from ordered list
        for c in marker_stripped:
            if not c.isdigit():
                return c == ordered_marker_char
        return False
    else:
        return marker_stripped[0] == bullet_char


def extract_task_marker(line: str) -> tuple[bool | None, str]:
    """Extract task list marker from line content.

    Args:
        line: The line content (stripped of marker)

    Returns:
        Tuple of (checked status or None, remaining content)
        - checked is False for [ ]
        - checked is True for [x] or [X]
        - checked is None if no task marker
    """
    if line.startswith("[ ] "):
        return (False, line[4:])
    elif line.startswith("[x] ") or line.startswith("[X] "):
        return (True, line[4:])
    return (None, line)
