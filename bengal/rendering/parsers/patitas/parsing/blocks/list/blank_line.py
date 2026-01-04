"""Blank line handling for list parsing.

Handles the complex logic for blank lines within and between list items.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.parsing.blocks.list.marker import (
    get_marker_indent,
    is_list_marker,
)
from bengal.rendering.parsers.patitas.tokens import TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.tokens import Token


class BlankLineResult:
    """Base class for blank line handling results."""

    pass


class ContinueList(BlankLineResult):
    """Continue parsing the current list (may mark as loose)."""

    def __init__(self, is_loose: bool = False, save_paragraph: bool = False):
        self.is_loose = is_loose
        self.save_paragraph = save_paragraph


class EndItem(BlankLineResult):
    """End the current list item but continue the list."""

    def __init__(self, is_loose: bool = True):
        self.is_loose = is_loose


class EndList(BlankLineResult):
    """End the entire list."""

    pass


class ParseBlock(BlankLineResult):
    """Parse the next token as a block element within the list item."""

    def __init__(self, is_loose: bool = True):
        self.is_loose = is_loose


class ParseContinuation(BlankLineResult):
    """Parse the next token as continuation content."""

    def __init__(self, is_loose: bool = True, save_paragraph: bool = True):
        self.is_loose = is_loose
        self.save_paragraph = save_paragraph


def handle_blank_line(
    next_token: Token | None,
    source: str,
    start_indent: int,
    content_indent: int,
    actual_content_indent: int | None,
) -> BlankLineResult:
    """Handle blank line in list parsing.

    Determines what action to take after encountering a blank line
    within a list item.

    Args:
        next_token: The token following the blank line(s)
        source: The full source text
        start_indent: Indent level of the list's first marker
        content_indent: Minimum indent for continuation content
        actual_content_indent: Actual content indent from first line (if known)

    Returns:
        BlankLineResult indicating how to proceed
    """
    if next_token is None:
        return EndList()

    check_indent = actual_content_indent if actual_content_indent is not None else content_indent

    match next_token.type:
        case TokenType.LINK_REFERENCE_DEF:
            # CommonMark: Link reference definitions don't interrupt lists
            return ContinueList(is_loose=True)

        case TokenType.LIST_ITEM_MARKER:
            next_indent = get_marker_indent(next_token.value)
            if next_indent < start_indent:
                # Less than start_indent - belongs to outer list (ends this list)
                return EndList()
            if next_indent < check_indent:
                # Less than content_indent but >= start_indent - sibling item (ends current item)
                return EndItem(is_loose=True)
            # At or beyond content_indent - could be nested list
            return ContinueList(is_loose=True)

        case TokenType.PARAGRAPH_LINE:
            # Use pre-computed line_indent from lexer
            para_indent = next_token.line_indent
            if para_indent < check_indent:
                # Not indented enough - terminates the list
                return EndList()
            # Indented enough - continuation paragraph (loose list)
            return ParseContinuation(is_loose=True, save_paragraph=True)

        case (
            TokenType.FENCED_CODE_START
            | TokenType.BLOCK_QUOTE_MARKER
            | TokenType.ATX_HEADING
            | TokenType.THEMATIC_BREAK
        ):
            # Block types that can appear in list items after blank line
            return ParseBlock(is_loose=True)

        case TokenType.INDENTED_CODE:
            return _handle_blank_then_indented_code(
                next_token,
                source,
                start_indent,
                content_indent,
                actual_content_indent,
            )

        case _:
            return EndList()


def _handle_blank_then_indented_code(
    token: Token,
    source: str,
    start_indent: int,
    content_indent: int,
    actual_content_indent: int | None,
) -> BlankLineResult:
    """Handle INDENTED_CODE token after blank line.

    This is complex because INDENTED_CODE may be:
    - A list marker continuation (at list level)
    - Paragraph continuation (at content level)
    - Block quote or fenced code
    - Actual indented code block (4+ beyond content)

    Args:
        token: The INDENTED_CODE token
        source: The full source text
        start_indent: Indent level of the list's first marker
        content_indent: Minimum indent for continuation content
        actual_content_indent: Actual content indent from first line (if known)

    Returns:
        BlankLineResult indicating how to proceed
    """
    check_indent = actual_content_indent if actual_content_indent is not None else content_indent

    # Use pre-computed line_indent from lexer
    original_indent = token.line_indent
    code_content = token.value.lstrip().rstrip()

    # Check if this is a list marker at the original list level
    if original_indent == start_indent and is_list_marker(code_content):
        # This is a sibling list item
        return EndItem(is_loose=True)

    # Check indent relative to content
    indent_beyond_content = original_indent - check_indent

    # After a blank line, content can only continue if at or beyond content indent
    # Content BELOW content indent terminates the item (falls through to EndList)

    # Check for special block elements at content level
    if original_indent >= check_indent:
        # Block quote
        if code_content.startswith(">"):
            return ParseBlock(is_loose=True)

        # Fenced code
        if code_content.startswith("```") or code_content.startswith("~~~"):
            return ParseBlock(is_loose=True)

        # Nested list marker
        if is_list_marker(code_content):
            return ParseBlock(is_loose=True)

        # Indented code (4+ beyond content)
        if indent_beyond_content >= 4:
            return ParseBlock(is_loose=True)

        # Default: paragraph continuation
        return ParseContinuation(is_loose=True, save_paragraph=True)

    # Not indented enough - terminates list
    return EndList()
