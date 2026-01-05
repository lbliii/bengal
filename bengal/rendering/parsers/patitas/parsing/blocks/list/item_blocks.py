"""Block element handling within list items.

Handles parsing of block elements (thematic breaks, fenced code, block quotes,
indented code) that appear within list items.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bengal.rendering.parsers.patitas.nodes import (
    BlockQuote,
    FencedCode,
    IndentedCode,
    Paragraph,
    ThematicBreak,
)
from bengal.rendering.parsers.patitas.tokens import TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.nodes import Block, Inline
    from bengal.rendering.parsers.patitas.tokens import Token


class ParserProtocol(Protocol):
    """Protocol for parser methods needed by block handlers."""

    _source: str

    def _at_end(self) -> bool: ...
    def _advance(self) -> Token | None: ...
    def _parse_inline(self, text: str, location: object) -> tuple[Inline, ...]: ...
    def _parse_fenced_code(self, override_fence_indent: int | None = None) -> FencedCode: ...
    def _get_line_at(self, offset: int) -> str: ...
    def _strip_columns(self, text: str, count: int) -> str: ...

    @property
    def _current(self) -> Token | None: ...


def handle_thematic_break(
    token: Token,
    saw_paragraph_content: bool,
    has_content_lines: bool,
    parser: ParserProtocol,
) -> tuple[Block | None, bool]:
    """Handle a thematic break token within a list item.

    Args:
        token: The THEMATIC_BREAK token
        saw_paragraph_content: Whether paragraph content was seen before this
        has_content_lines: Whether there are accumulated content lines
        parser: The parser instance

    Returns:
        Tuple of (block to add or None, should_continue)
        - If should_continue is False, the list should terminate
    """
    if not saw_paragraph_content and not has_content_lines:
        # Thematic break immediately after list marker - include in item
        parser._advance()
        return (ThematicBreak(location=token.location), True)
    else:
        # Thematic break after paragraph content - terminates list
        return (None, False)


def handle_fenced_code_immediate(
    token: Token,
    saw_paragraph_content: bool,
    has_content_lines: bool,
    content_indent: int,
    parser: ParserProtocol,
) -> tuple[Block | None, bool]:
    """Handle a fenced code block immediately after list marker.

    Args:
        token: The FENCED_CODE_START token
        saw_paragraph_content: Whether paragraph content was seen before this
        has_content_lines: Whether there are accumulated content lines
        content_indent: Content indent for the list item
        parser: The parser instance

    Returns:
        Tuple of (block to add or None, should_continue)
        - If should_continue is False, the list should terminate
    """
    if not saw_paragraph_content and not has_content_lines:
        # Fenced code block immediately after list marker
        block = parser._parse_fenced_code(override_fence_indent=content_indent)
        return (block, True)
    else:
        # After paragraph content - terminates list
        return (None, False)


def parse_block_quote_from_indented_code(
    start_token: Token,
    parser: ParserProtocol,
    check_indent: int,
) -> BlockQuote:
    """Parse a block quote from INDENTED_CODE tokens.

    Used when block quote markers appear at content indent level within
    list items, where the lexer produces INDENTED_CODE tokens.

    Args:
        start_token: The first INDENTED_CODE token with block quote content
        parser: The parser instance
        check_indent: The content indent level

    Returns:
        A BlockQuote node
    """
    bq_lines: list[str] = []
    code_content = start_token.value.lstrip().rstrip()

    # Extract initial content
    if code_content.startswith("> "):
        bq_lines.append(code_content[2:])
    else:
        bq_lines.append(code_content[1:])
    parser._advance()

    # Collect remaining block quote lines
    while not parser._at_end():
        bq_tok = parser._current
        if bq_tok is None:
            break

        if bq_tok.type == TokenType.INDENTED_CODE:
            bq_original_indent = bq_tok.line_indent
            bq_content = bq_tok.value.lstrip().rstrip()
            if bq_original_indent >= check_indent and bq_content.startswith(">"):
                if bq_content.startswith("> "):
                    bq_lines.append(bq_content[2:])
                else:
                    bq_lines.append(bq_content[1:])
                parser._advance()
            else:
                break
        elif bq_tok.type == TokenType.BLANK_LINE:
            parser._advance()
            break
        else:
            break

    bq_text = "\n".join(bq_lines)
    bq_inlines = parser._parse_inline(bq_text, start_token.location)
    bq_para = Paragraph(location=start_token.location, children=bq_inlines)
    return BlockQuote(location=start_token.location, children=(bq_para,))


def parse_fenced_code_from_indented_code(
    start_token: Token,
    parser: ParserProtocol,
    check_indent: int,
) -> FencedCode:
    """Parse a fenced code block from INDENTED_CODE tokens.

    Used when fenced code appears at content indent level within list items.

    Args:
        start_token: The first INDENTED_CODE token with fence markers
        parser: The parser instance
        check_indent: The content indent level

    Returns:
        A FencedCode node
    """
    code_content = start_token.value.lstrip().rstrip()
    fence_char = code_content[0]
    fence_count = len(code_content) - len(code_content.lstrip(fence_char))
    info_string = code_content[fence_count:].strip() or None

    parser._advance()

    source_start: int | None = None
    source_end = 0

    while not parser._at_end():
        fc_tok = parser._current
        if fc_tok is None:
            break

        if fc_tok.type == TokenType.INDENTED_CODE:
            fc_content = fc_tok.value.lstrip().rstrip()
            # Check for closing fence
            if fc_content.startswith(fence_char * fence_count) and not fc_content.strip(fence_char):
                parser._advance()
                break
            # Accumulate content
            if source_start is None:
                source_start = fc_tok.location.offset
            source_end = fc_tok.location.end_offset
            parser._advance()
        elif fc_tok.type == TokenType.BLANK_LINE:
            parser._advance()
        else:
            break

    return FencedCode(
        location=start_token.location,
        source_start=source_start or 0,
        source_end=source_end,
        info=info_string,
        marker=fence_char,
        fence_indent=check_indent,
    )


def parse_indented_code_in_list(
    start_token: Token,
    parser: ParserProtocol,
    check_indent: int,
) -> IndentedCode:
    """Parse an indented code block within a list item.

    Args:
        start_token: The first INDENTED_CODE token
        parser: The parser instance
        check_indent: The content indent level

    Returns:
        An IndentedCode node
    """
    code_lines: list[str] = [start_token.value]
    parser._advance()

    while not parser._at_end():
        tok = parser._current
        if tok is None:
            break

        if tok.type == TokenType.INDENTED_CODE:
            tok_indent = tok.line_indent
            if tok_indent >= check_indent + 4:
                code_lines.append(tok.value)
                parser._advance()
            else:
                break
        elif tok.type == TokenType.BLANK_LINE:
            # CommonMark: blank lines within indented code are preserved.
            # Consume all consecutive blank lines and check if more code follows.
            blank_count = 0
            while not parser._at_end() and parser._current is not None:
                if parser._current.type == TokenType.BLANK_LINE:
                    blank_count += 1
                    parser._advance()
                else:
                    break

            # Check if next token is more indented code
            if not parser._at_end() and parser._current is not None:
                next_tok = parser._current
                if next_tok.type == TokenType.INDENTED_CODE:
                    tok_indent = next_tok.line_indent
                    if tok_indent >= check_indent + 4:
                        # Include blank lines and continue
                        code_lines.append("\n" * blank_count)
                        continue
            # No more code follows - exit
            break
        else:
            break

    # Strip check_indent columns from each line
    adjusted_lines: list[str] = []
    for code_line in code_lines:
        if code_line == "\n":
            adjusted_lines.append("\n")
        else:
            adjusted_lines.append(parser._strip_columns(code_line, check_indent))

    adjusted_code = "".join(adjusted_lines)
    return IndentedCode(location=start_token.location, code=adjusted_code)
