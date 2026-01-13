"""Nested list handling for list parsing.

Handles detection and parsing of nested lists within list items.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bengal.rendering.parsers.patitas.nodes import List, ListItem, Paragraph
from bengal.rendering.parsers.patitas.parsing.blocks.list.marker import (
    is_list_marker,
)
from bengal.rendering.parsers.patitas.tokens import TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.nodes import Block, Inline
    from bengal.rendering.parsers.patitas.tokens import Token


class ParserProtocol(Protocol):
    """Protocol for parser methods needed by nested list handlers."""

    _source: str

    def _at_end(self) -> bool: ...
    def _advance(self) -> Token | None: ...
    def _parse_inline(self, text: str, location: object) -> tuple[Inline, ...]: ...

    @property
    def _current(self) -> Token | None: ...


def detect_nested_block_in_content(
    line: str,
    line_indent: int,
    content_indent: int,
) -> bool:
    """Detect if paragraph line content is actually a nested block marker.
    
    CommonMark: If the first content after a list marker is itself a block
    marker (list, blockquote, heading, etc.), it should be parsed as a nested
    block, BUT only if it's indented appropriately (not 4+ spaces beyond
    content indent).
    
    Args:
        line: The stripped line content
        line_indent: Indent of the line (from tok.line_indent)
        content_indent: Content indent of the current list item
    
    Returns:
        True if this should be parsed as a nested block
        
    """
    if not line:
        return False

    # If line is indented 4+ spaces beyond content indent, it's literal text
    if line_indent >= content_indent + 4:
        return False

    # Check for list markers
    if is_list_marker(line):
        return True

    # Check for blockquote markers
    if line.startswith(">"):
        return True

    # Check for ATX headings
    if line.startswith("#"):
        # Must be valid ATX heading (1-6 # followed by space or end of line)
        pos = 0
        while pos < len(line) and line[pos] == "#" and pos < 6:
            pos += 1
        if pos > 0 and (pos == len(line) or line[pos] in " \t"):
            return True

    # Check for thematic breaks
    from bengal.rendering.parsers.patitas.parsing.charsets import THEMATIC_BREAK_CHARS

    if line[0] in THEMATIC_BREAK_CHARS:
        # Simplified thematic break check
        stripped = line.replace(" ", "").replace("\t", "")
        if len(stripped) >= 3 and all(c == stripped[0] for c in stripped):
            return True

    return False


def parse_nested_list_inline(
    line: str,
    token_location: object,
    parser: ParserProtocol,
    directive_registry: object | None,
    strict_contracts: bool,
    tables_enabled: bool,
    strikethrough_enabled: bool,
    task_lists_enabled: bool,
) -> list[Block]:
    """Parse a nested list from inline content.
    
    Used when a paragraph line turns out to be a nested list marker.
    
    Args:
        line: The content line that is a list marker
        token_location: Location of the token
        parser: The parser instance
        directive_registry: Registry for directives
        strict_contracts: Whether to enforce strict contracts
        tables_enabled: Whether tables are enabled
        strikethrough_enabled: Whether strikethrough is enabled
        task_lists_enabled: Whether task lists are enabled
    
    Returns:
        List of parsed blocks
        
    """
    # Import here to avoid circular dependency
    from bengal.rendering.parsers.patitas.parser import Parser

    nested_parser = Parser(
        line + "\n",
        directive_registry=directive_registry,
        strict_contracts=strict_contracts,
    )
    nested_parser._tables_enabled = tables_enabled
    nested_parser._strikethrough_enabled = strikethrough_enabled
    nested_parser._task_lists_enabled = task_lists_enabled
    return list(nested_parser.parse())


def parse_nested_list_from_indented_code(
    token: Token,
    original_indent: int,
    parent_content_indent: int,
    parser: ParserProtocol,
) -> List | None:
    """Parse a nested list from an INDENTED_CODE token containing a list marker.
    
    When the lexer produces INDENTED_CODE for 4+ space indented lines, those
    lines may actually be nested list markers in list context.
    
    Args:
        token: The INDENTED_CODE token containing the list marker
        original_indent: The original indentation of the line in source
        parent_content_indent: The content indent of the parent list item
        parser: The parser instance
    
    Returns:
        A List node containing the nested list, or None if parsing fails.
        
    """
    stripped = token.value.lstrip()

    # Determine list type and extract marker info
    first_char = stripped[0]
    if first_char in "-*+":
        ordered = False
        marker_char = first_char
        marker_len = 1
        remaining = stripped[2:] if len(stripped) > 2 else ""
    else:
        ordered = True
        pos = 0
        while pos < len(stripped) and stripped[pos].isdigit():
            pos += 1
        marker_char = stripped[pos] if pos < len(stripped) else "."
        marker_len = pos + 1
        remaining = stripped[pos + 2 :] if pos + 2 < len(stripped) else ""

    nested_content_indent = original_indent + marker_len + 1

    items: list[ListItem] = []
    tight = True
    start = 1

    if ordered:
        num_str = ""
        for c in stripped:
            if c.isdigit():
                num_str += c
            else:
                break
        if num_str:
            start = int(num_str)

    # Process first item
    first_item_children: list[Block] = []
    if remaining.strip():
        first_item_inlines = parser._parse_inline(remaining.strip(), token.location)
        first_item_children.append(Paragraph(location=token.location, children=first_item_inlines))

    parser._advance()

    content_lines: list[str] = []
    current_token = token

    while not parser._at_end():
        tok = parser._current
        if tok is None:
            break

        if tok.type == TokenType.INDENTED_CODE:
            tok_original_indent = tok.line_indent
            tok_content = tok.value.lstrip()

            # Check for sibling marker
            is_sibling = _is_sibling_marker(
                tok_content, tok_original_indent, original_indent, ordered, marker_char
            )

            if is_sibling:
                # Finalize current item
                if content_lines:
                    cl_content = "\n".join(content_lines)
                    cl_inlines = parser._parse_inline(cl_content, tok.location)
                    first_item_children.append(
                        Paragraph(location=tok.location, children=cl_inlines)
                    )
                    content_lines = []

                items.append(
                    ListItem(
                        location=current_token.location,
                        children=tuple(first_item_children),
                        checked=None,
                    )
                )

                # Start new item
                new_remaining = _extract_remaining_content(tok_content, ordered)
                first_item_children = []
                if new_remaining:
                    new_inlines = parser._parse_inline(new_remaining, tok.location)
                    first_item_children.append(
                        Paragraph(location=tok.location, children=new_inlines)
                    )
                parser._advance()
                current_token = tok
                continue

            # Check for deeper nested list
            if tok_original_indent >= nested_content_indent and is_list_marker(tok_content):
                if content_lines:
                    cl_content = "\n".join(content_lines)
                    cl_inlines = parser._parse_inline(cl_content, tok.location)
                    first_item_children.append(
                        Paragraph(location=tok.location, children=cl_inlines)
                    )
                    content_lines = []

                nested = parse_nested_list_from_indented_code(
                    tok, tok_original_indent, nested_content_indent, parser
                )
                if nested:
                    first_item_children.append(nested)
                continue

            # Continuation content
            if tok_original_indent >= parent_content_indent:
                content_lines.append(tok_content.rstrip())
                parser._advance()
            else:
                break

        elif tok.type == TokenType.PARAGRAPH_LINE:
            content_lines.append(tok.value.lstrip().rstrip())
            parser._advance()

        elif tok.type == TokenType.BLANK_LINE:
            tight = False
            parser._advance()

        else:
            break

    # Finalize last item
    if content_lines:
        cl_content = "\n".join(content_lines)
        cl_inlines = parser._parse_inline(cl_content, current_token.location)
        first_item_children.append(Paragraph(location=current_token.location, children=cl_inlines))

    items.append(
        ListItem(
            location=current_token.location,
            children=tuple(first_item_children),
            checked=None,
        )
    )

    return List(
        location=token.location,
        items=tuple(items),
        ordered=ordered,
        start=start,
        tight=tight,
    )


def _is_sibling_marker(
    content: str,
    content_indent: int,
    expected_indent: int,
    ordered: bool,
    marker_char: str,
) -> bool:
    """Check if content is a sibling list marker at the expected indent."""
    if content_indent != expected_indent:
        return False

    if not content:
        return False

    first_char = content[0]

    if not ordered:
        return (
            first_char in "-*+"
            and first_char == marker_char
            and len(content) > 1
            and content[1] in " \t"
        )

    if first_char.isdigit():
        pos = 0
        while pos < len(content) and content[pos].isdigit():
            pos += 1
        return (
            pos < len(content)
            and content[pos] == marker_char
            and pos + 1 < len(content)
            and content[pos + 1] in " \t"
        )

    return False


def _extract_remaining_content(content: str, ordered: bool) -> str:
    """Extract content after the list marker."""
    first_char = content[0]

    if first_char in "-*+":
        return content[2:].strip() if len(content) > 2 else ""

    pos = 0
    while pos < len(content) and content[pos].isdigit():
        pos += 1
    return content[pos + 2 :].strip() if pos + 2 < len(content) else ""
