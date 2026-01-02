"""Core block parsing for Patitas parser.

Provides block dispatch and basic block parsing (headings, code, quotes, paragraphs).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.nodes import (
    Block,
    BlockQuote,
    FencedCode,
    Heading,
    IndentedCode,
    Paragraph,
    Table,
    ThematicBreak,
)
from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    pass


# Pattern to find backslash escapes (CommonMark ASCII punctuation)
_ESCAPE_PATTERN = re.compile(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])")


def _process_escapes(text: str) -> str:
    """Process backslash escapes in info strings.

    CommonMark: Backslash escapes work in code fence info strings.
    """
    return _ESCAPE_PATTERN.sub(r"\1", text)


class BlockParsingCoreMixin:
    """Core block parsing methods.

    Required Host Attributes:
        - _source: str
        - _tokens: list[Token]
        - _pos: int
        - _current: Token | None
        - _tables_enabled: bool

    Required Host Methods:
        - _at_end() -> bool
        - _advance() -> Token | None
        - _parse_inline(text, location) -> tuple[Inline, ...]
        - _parse_list(parent_indent) -> List
        - _parse_directive() -> Directive
        - _parse_footnote_def() -> FootnoteDef
        - _try_parse_table(lines, location) -> Table | None
    """

    _source: str
    _tokens: list[Token]
    _pos: int
    _current: Token | None
    _tables_enabled: bool

    def _parse_block(self) -> Block | None:
        """Parse a single block element."""
        if self._at_end():
            return None

        token = self._current
        assert token is not None

        match token.type:
            case TokenType.BLANK_LINE:
                self._advance()
                return None  # Skip blank lines

            case TokenType.ATX_HEADING:
                return self._parse_atx_heading()

            case TokenType.FENCED_CODE_START:
                return self._parse_fenced_code()

            case TokenType.THEMATIC_BREAK:
                return self._parse_thematic_break()

            case TokenType.BLOCK_QUOTE_MARKER:
                return self._parse_block_quote()

            case TokenType.LIST_ITEM_MARKER:
                return self._parse_list()

            case TokenType.INDENTED_CODE:
                return self._parse_indented_code()

            case TokenType.PARAGRAPH_LINE:
                return self._parse_paragraph()

            case TokenType.DIRECTIVE_OPEN:
                return self._parse_directive()

            case TokenType.FOOTNOTE_DEF:
                return self._parse_footnote_def()

            case TokenType.LINK_REFERENCE_DEF:
                # Link reference definitions are collected in first pass
                # They don't produce AST nodes, just skip
                self._advance()
                return None

            case _:
                # Skip unknown tokens
                self._advance()
                return None

    def _parse_atx_heading(self) -> Heading:
        """Parse ATX heading (# Heading)."""
        token = self._current
        assert token is not None and token.type == TokenType.ATX_HEADING
        self._advance()

        # Extract level and content from token value
        value = token.value
        level = 0
        pos = 0

        while pos < len(value) and value[pos] == "#" and level < 6:
            level += 1
            pos += 1

        # Skip space after #
        if pos < len(value) and value[pos] == " ":
            pos += 1

        # CommonMark: leading and trailing spaces are stripped from heading content
        content = value[pos:].strip()

        # Parse inline content
        children = self._parse_inline(content, token.location)

        return Heading(
            location=token.location,
            level=level,  # type: ignore[arg-type]
            children=children,
            style="atx",
        )

    def _parse_fenced_code(self) -> FencedCode:
        """Parse fenced code block with zero-copy coordinates."""
        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.FENCED_CODE_START
        self._advance()

        # Extract marker and info from start token
        value = start_token.value
        marker = value[0]  # ` or ~
        info: str | None = None

        # Count marker chars
        marker_count = 0
        while marker_count < len(value) and value[marker_count] == marker:
            marker_count += 1

        # Rest is info string
        info_str = value[marker_count:].strip()
        if info_str:
            # CommonMark: process backslash escapes in info string
            info = _process_escapes(info_str)

        # Track content boundaries (ZERO-COPY: no string accumulation)
        content_start: int | None = None
        content_end: int = 0

        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.FENCED_CODE_END:
                # If we have no content tokens, content_end should be where the fence ends
                if content_start is None:
                    content_start = start_token.location.end_offset
                    content_end = content_start
                self._advance()
                break
            elif token.type == TokenType.FENCED_CODE_CONTENT:
                if content_start is None:
                    content_start = token.location.offset
                content_end = token.location.end_offset
                self._advance()
            elif token.type == TokenType.SUB_LEXER_TOKENS:
                # This shouldn't happen in the new "dumb" lexer mode,
                # but we handle it for robustness if someone uses an old lexer.
                self._advance()
            else:
                # Unexpected token, stop
                break

        return FencedCode(
            location=start_token.location,
            source_start=content_start if content_start is not None else 0,
            source_end=content_end,
            info=info,
            marker=marker,  # type: ignore[arg-type]
        )

    def _parse_thematic_break(self) -> ThematicBreak:
        """Parse thematic break (---, ***, ___)."""
        token = self._current
        assert token is not None and token.type == TokenType.THEMATIC_BREAK
        self._advance()

        return ThematicBreak(location=token.location)

    def _parse_block_quote(self) -> BlockQuote:
        """Parse block quote (> quoted)."""
        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.BLOCK_QUOTE_MARKER
        self._advance()

        # Collect content after > into paragraph lines
        content_lines: list[str] = []

        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.PARAGRAPH_LINE:
                content_lines.append(token.value.lstrip())
                self._advance()
            elif token.type == TokenType.BLOCK_QUOTE_MARKER:
                # Continuation of block quote
                self._advance()
            elif token.type == TokenType.BLANK_LINE:
                # End of block quote
                break
            else:
                break

        # Parse content as blocks
        content = "\n".join(content_lines)
        if content:
            # Create a paragraph from the content
            children = self._parse_inline(content, start_token.location)
            para = Paragraph(location=start_token.location, children=children)
            return BlockQuote(location=start_token.location, children=(para,))

        return BlockQuote(location=start_token.location, children=())

    def _parse_indented_code(self) -> IndentedCode:
        """Parse indented code block."""
        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.INDENTED_CODE

        content_parts: list[str] = []

        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.INDENTED_CODE:
                content_parts.append(token.value)
                self._advance()
            elif token.type == TokenType.BLANK_LINE:
                # Blank line might continue indented code
                # Look ahead to see if there's more indented code
                next_pos = self._pos + 1
                if next_pos < len(self._tokens):
                    next_token = self._tokens[next_pos]
                    if next_token.type == TokenType.INDENTED_CODE:
                        content_parts.append("\n")
                        self._advance()
                        continue
                break
            else:
                break

        code = "".join(content_parts)
        # CommonMark: preserve trailing newline in indented code blocks
        # (don't strip it like we do for fenced code)

        return IndentedCode(location=start_token.location, code=code)

    def _parse_paragraph(self) -> Paragraph | Table | Heading:
        """Parse paragraph (consecutive text lines), table, or setext heading.

        If the second line is a setext underline (=== or ---), returns Heading.
        If tables are enabled and lines form a valid GFM table, returns Table.
        Otherwise returns Paragraph.

        CommonMark: Ordered lists can only interrupt paragraphs if they start with 1.
        """
        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.PARAGRAPH_LINE

        lines: list[str] = []

        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.PARAGRAPH_LINE:
                lines.append(token.value.lstrip())
                self._advance()
            elif token.type == TokenType.LIST_ITEM_MARKER:
                # CommonMark: ordered lists can only interrupt paragraphs if start=1
                # Check if this is an ordered list that doesn't start with 1
                marker = token.value.lstrip()
                if marker[0].isdigit():
                    # Ordered list - extract the number
                    num_str = ""
                    for c in marker:
                        if c.isdigit():
                            num_str += c
                        else:
                            break
                    if num_str and int(num_str) != 1:
                        # Ordered list not starting with 1 - treat as paragraph continuation
                        # The lexer emits the full "14. content" as marker + content tokens
                        # We need to reconstruct the original line
                        line_parts = [token.value.lstrip()]
                        self._advance()
                        # The content after the marker is the next token
                        if not self._at_end():
                            next_token = self._current
                            if (
                                next_token is not None
                                and next_token.type == TokenType.PARAGRAPH_LINE
                            ):
                                line_parts.append(next_token.value)
                                self._advance()
                        lines.append("".join(line_parts))
                        continue
                # Valid list interruption - stop paragraph
                break
            else:
                break

        # Check for setext heading: text followed by === or ---
        if len(lines) >= 2:
            last_line = lines[-1].strip()
            if self._is_setext_underline(last_line):
                # Determine heading level: === is h1, --- is h2
                level = 1 if last_line[0] == "=" else 2
                # Heading text is everything except the underline
                # CommonMark: strip trailing whitespace from each line
                heading_lines = [line.rstrip() for line in lines[:-1]]
                heading_text = "\n".join(heading_lines)
                children = self._parse_inline(heading_text, start_token.location)
                return Heading(
                    location=start_token.location,
                    level=level,
                    children=children,
                    style="setext",
                )

        # Check if next token is THEMATIC_BREAK (---) which could be setext h2
        # CommonMark: --- after paragraph is setext heading, not thematic break
        if len(lines) == 1 and not self._at_end():
            token = self._current
            if (
                token is not None
                and token.type == TokenType.THEMATIC_BREAK
                and token.value.strip().startswith("-")
            ):
                self._advance()  # Consume the thematic break
                # CommonMark: strip trailing whitespace from heading content
                heading_text = lines[0].rstrip()
                children = self._parse_inline(heading_text, start_token.location)
                return Heading(
                    location=start_token.location,
                    level=2,
                    children=children,
                    style="setext",
                )

        # Check for table structure if tables enabled
        if self._tables_enabled and len(lines) >= 2 and "|" in lines[0]:
            table = self._try_parse_table(lines, start_token.location)
            if table:
                return table

        content = "\n".join(lines)
        # CommonMark: trailing spaces at end of paragraph are stripped
        # (but trailing spaces followed by content create hard breaks, handled in inline)
        content = content.rstrip(" ")
        children = self._parse_inline(content, start_token.location)

        return Paragraph(location=start_token.location, children=children)

    def _is_setext_underline(self, line: str) -> bool:
        """Check if line is a setext heading underline.

        Must be at least 1 character of = or - with optional trailing spaces.
        CommonMark allows up to 3 leading spaces.
        """
        # Strip leading spaces (up to 3)
        stripped = line.lstrip()
        if len(line) - len(stripped) > 3:
            return False
        if not stripped:
            return False
        char = stripped[0]
        if char not in "=-":
            return False
        # All remaining characters must be the same (= or -)
        return all(c == char for c in stripped.rstrip())
