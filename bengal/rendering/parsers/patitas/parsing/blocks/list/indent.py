"""Indent calculation utilities for list parsing.

Provides functions for calculating and managing indentation levels.
"""

from __future__ import annotations

from bengal.rendering.parsers.patitas.parsing.blocks.list.marker import get_marker_indent


def calculate_content_indent(
    source: str,
    marker_stripped: str,
    marker_indent: int,
    line_offset: int,
) -> int:
    """Calculate the content indent for a list item.

    CommonMark: The content indent is the column position of the first
    non-space character after the marker. If the line is empty after
    the marker, it's marker_end_col + 1.

    Args:
        source: The full source text
        marker_stripped: The marker with leading whitespace stripped
        marker_indent: The indent level of the marker
        line_offset: The offset in source where this token starts

    Returns:
        The column position where content should start
    """
    # Find the start of the line containing this offset
    line_start_pos = source.rfind("\n", 0, line_offset) + 1
    if line_start_pos == 0:
        line_start_pos = 0
    original_line = source[line_start_pos:].split("\n")[0]

    # Find where content starts (after marker and spaces)
    marker_part = marker_stripped.split()[0] if marker_stripped.split() else marker_stripped
    marker_pos_in_line = original_line.find(marker_part)
    if marker_pos_in_line == -1:
        # Fallback: use marker_indent + marker_length + 1
        return marker_indent + len(marker_part) + 1

    marker_end_col = get_marker_indent(original_line[: marker_pos_in_line + len(marker_part)])

    # Content starts after the marker
    rest_of_line = original_line[marker_pos_in_line + len(marker_part) :]
    if not rest_of_line or rest_of_line.isspace():
        return marker_end_col + 1

    # Find first non-space char in rest_of_line
    spaces_after = len(rest_of_line) - len(rest_of_line.lstrip(" "))
    # CommonMark: If more than 4 spaces, it's 1 space and the rest is indented content
    if spaces_after > 4:
        return marker_end_col + 1

    return marker_end_col + spaces_after


def is_continuation_indent(
    line_indent: int,
    content_indent: int,
    start_indent: int,
) -> bool:
    """Check if a line's indent qualifies as continuation content.

    CommonMark: Content indented at least as much as the list item's
    content indentation is continuation content.

    Args:
        line_indent: The indent of the line in question
        content_indent: The content indent of the current list item
        start_indent: The indent of the list's first marker

    Returns:
        True if the line is continuation content
    """
    # Line must be at or beyond content_indent
    # But not so far that it becomes indented code (4+ beyond content_indent)
    indent_beyond_content = line_indent - content_indent
    return (
        line_indent >= start_indent and line_indent <= content_indent and indent_beyond_content < 4
    )


def is_nested_list_indent(line_indent: int, content_indent: int) -> bool:
    """Check if a line's indent qualifies for starting a nested list.

    CommonMark: A list marker at content_indent or deeper can be a nested list.

    Args:
        line_indent: The indent of the line in question
        content_indent: The content indent of the current list item

    Returns:
        True if a list marker at this indent would be nested
    """
    return line_indent >= content_indent


def is_indented_code_indent(line_indent: int, content_indent: int) -> bool:
    """Check if a line's indent qualifies as indented code.

    CommonMark: Content indented 4+ spaces beyond content_indent is
    indented code block.

    Args:
        line_indent: The indent of the line in question
        content_indent: The content indent of the current list item

    Returns:
        True if the line should be treated as indented code
    """
    return line_indent >= content_indent + 4
