"""Blank line handling for list parsing.

Handles the complex logic for blank lines within and between list items.

Phase 4: Uses ContainerStack for indent queries (stack is source of truth).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.parsing.blocks.list.marker import (
    get_marker_indent,
    is_list_marker,
)
from bengal.rendering.parsers.patitas.tokens import TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.parsing.containers import ContainerStack
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
    containers: ContainerStack,
) -> BlankLineResult:
    """Handle blank line in list parsing using ContainerStack.

    Determines what action to take after encountering a blank line
    within a list item. Queries indent values from the container stack
    (the stack is the source of truth for indent context).

    Args:
        next_token: The token following the blank line(s)
        containers: The container stack with current frame context

    Returns:
        BlankLineResult indicating how to proceed
    """
    if next_token is None:
        return EndList()

    current = containers.current()
    start_indent = current.start_indent
    check_indent = current.content_indent  # Already updated with actual value

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
                # Less than content_indent but >= start_indent - sibling item
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
            # Respect indentation: block content must be at or beyond the list item's
            # content indent to stay in the item. Otherwise, the block terminates
            # the list and is parsed at the parent level (CommonMark 5.3/5.4).
            block_indent = next_token.line_indent if next_token.line_indent >= 0 else 0
            if block_indent < check_indent:
                return EndList()
            return ParseBlock(is_loose=True)

        case TokenType.INDENTED_CODE:
            return _handle_blank_then_indented_code(
                next_token,
                containers,
            )

        case _:
            return EndList()


def _handle_blank_then_indented_code(
    token: Token,
    containers: ContainerStack,
) -> BlankLineResult:
    """Handle INDENTED_CODE token after blank line using ContainerStack.

    This is complex because INDENTED_CODE may be:
    - A list marker continuation (at list level)
    - Paragraph continuation (at content level)
    - Block quote or fenced code
    - Actual indented code block (4+ beyond content)

    Args:
        token: The INDENTED_CODE token
        containers: The container stack with current frame context

    Returns:
        BlankLineResult indicating how to proceed
    """
    current = containers.current()
    start_indent = current.start_indent
    check_indent = current.content_indent

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
