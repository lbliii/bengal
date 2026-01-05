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
    HtmlBlock,
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


def _extract_explicit_id(content: str) -> tuple[str, str | None]:
    """Extract MyST-compatible explicit anchor ID from heading content.

    Syntax: ## Title {#custom-id}

    The {#id} must be at the end of the content, preceded by whitespace.
    ID must start with a letter, contain only letters, numbers, hyphens, underscores.

    Args:
        content: Heading content (already stripped)

    Returns:
        Tuple of (content_without_id, explicit_id or None)
    """
    # Quick rejection: must end with }
    if not content.endswith("}"):
        return content, None

    # Find the opening {#
    brace_pos = content.rfind("{#")
    if brace_pos == -1:
        return content, None

    # Must be preceded by whitespace (or at start)
    if brace_pos > 0 and content[brace_pos - 1] not in " \t":
        return content, None

    # Extract the ID (between {# and })
    id_start = brace_pos + 2
    id_end = len(content) - 1
    explicit_id = content[id_start:id_end]

    # Validate ID: must start with letter, contain only valid chars
    if not explicit_id or not explicit_id[0].isalpha():
        return content, None

    for char in explicit_id:
        if not (char.isalnum() or char in "-_"):
            return content, None

    # Strip the {#id} and trailing whitespace from content
    new_content = content[:brace_pos].rstrip()

    return new_content, explicit_id


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

            case TokenType.HTML_BLOCK:
                return self._parse_html_block()

            case _:
                # Skip unknown tokens
                self._advance()
                return None

    def _parse_atx_heading(self) -> Heading:
        """Parse ATX heading (# Heading).

        Supports MyST-compatible explicit anchor syntax: ## Title {#custom-id}
        """
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

        # Check for explicit {#custom-id} syntax at end of content
        explicit_id = None
        content, explicit_id = _extract_explicit_id(content)

        # Parse inline content
        children = self._parse_inline(content, token.location)

        return Heading(
            location=token.location,
            level=level,  # type: ignore[arg-type]
            children=children,
            style="atx",
            explicit_id=explicit_id,
        )

    def _parse_fenced_code(self, override_fence_indent: int | None = None) -> FencedCode:
        """Parse fenced code block with zero-copy coordinates.

        Args:
            override_fence_indent: If provided, use this instead of the token's indent.
                                  Used for fenced code blocks in list items.
        """
        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.FENCED_CODE_START
        self._advance()

        # Extract marker, info, and indent from start token
        # Token value format: "I{indent}:{fence}{info}"
        value = start_token.value
        fence_indent = 0

        # Check for encoded indent prefix
        if value.startswith("I") and ":" in value:
            prefix, rest = value.split(":", 1)
            fence_indent = int(prefix[1:])  # Extract number after 'I'
            value = rest

        # Override if provided (for list item context)
        if override_fence_indent is not None:
            fence_indent = override_fence_indent

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
            fence_indent=fence_indent,
        )

    def _parse_thematic_break(self) -> ThematicBreak:
        """Parse thematic break (---, ***, ___)."""
        token = self._current
        assert token is not None and token.type == TokenType.THEMATIC_BREAK
        self._advance()

        return ThematicBreak(location=token.location)

    def _parse_html_block(self) -> HtmlBlock:
        """Parse HTML block (raw HTML content passed through unchanged)."""
        token = self._current
        assert token is not None and token.type == TokenType.HTML_BLOCK
        self._advance()

        return HtmlBlock(location=token.location, html=token.value)

    def _parse_block_quote(self) -> BlockQuote:
        """Parse block quote (> quoted).

        CommonMark 5.1: Block quotes can contain any block-level content,
        including headings, code blocks, lists, and nested block quotes.
        """
        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.BLOCK_QUOTE_MARKER
        self._advance()

        # Collect content after > markers
        content_lines: list[str] = []
        last_marker_line: int | None = None  # Line number of last marker seen
        has_paragraph_content = False  # Track if we have paragraph content for lazy continuation

        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.PARAGRAPH_LINE:
                # Check if this PARAGRAPH_LINE is on a different line than the last marker
                # Line without > after a bare ">" line = end of block quote
                # CommonMark: not lazy continuation after blank in quote
                if last_marker_line is not None and token.location.lineno != last_marker_line:
                    break
                content_lines.append(token.value)
                last_marker_line = None
                has_paragraph_content = True
                self._advance()
            elif token.type == TokenType.BLOCK_QUOTE_MARKER:
                if last_marker_line is not None:
                    # Two consecutive markers = blank quoted line (just ">")
                    # This creates a paragraph break in the quote content
                    content_lines.append("")
                    has_paragraph_content = False  # Reset - blank line breaks paragraph
                last_marker_line = token.location.lineno
                self._advance()
            elif token.type == TokenType.INDENTED_CODE:
                # CommonMark lazy continuation: INDENTED_CODE on a line without >
                # can continue a paragraph if we have active paragraph content.
                # The indented content becomes literal text in the paragraph.
                # BUT: lazy continuation only works with paragraphs, not with
                # indented code (content_lines[-1] starting with 4+ spaces).
                if has_paragraph_content and last_marker_line is None and content_lines:
                    last_line = content_lines[-1]
                    # Check if last content is a paragraph (not indented code)
                    # Indented code starts with 4+ spaces
                    leading_spaces = len(last_line) - len(last_line.lstrip(" "))
                    if leading_spaces < 4:
                        # Lazy continuation - append to last paragraph line.
                        # Use \x00 marker to prevent sub-parser from treating as block element.
                        # The renderer will strip these markers.
                        lazy_content = token.value.rstrip("\n")
                        # Escape list markers and other block-starting chars
                        if lazy_content.lstrip().startswith(("-", "*", "+", ">")):
                            lazy_content = "\x00" + lazy_content
                        content_lines[-1] = content_lines[-1] + "\n" + lazy_content
                        self._advance()
                        continue
                # Not lazy continuation - end block quote
                break
            elif token.type == TokenType.BLANK_LINE:
                # End of block quote
                break
            else:
                break

        # Parse content as blocks using recursive sub-parser
        content = "\n".join(content_lines)
        if content.strip():
            # Use sub-parser to parse nested block content
            children = self._parse_nested_content(content, start_token.location)
            return BlockQuote(location=start_token.location, children=children)

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
        # Track if the last line came from INDENTED_CODE (4+ spaces indent)
        # Such lines cannot be setext underlines
        last_line_was_indented_code = False

        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.PARAGRAPH_LINE:
                lines.append(token.value.lstrip())
                last_line_was_indented_code = False
                self._advance()
            elif token.type == TokenType.INDENTED_CODE:
                # CommonMark: indented code blocks cannot interrupt paragraphs
                # Treat indented content as paragraph continuation
                # The lexer produces INDENTED_CODE for 4+ space indent, but within
                # a paragraph this should be paragraph text with leading spaces stripped
                code_content = token.value.rstrip("\n")
                lines.append(code_content)
                last_line_was_indented_code = True  # Mark that this line was 4+ spaces
                self._advance()
            elif token.type == TokenType.LIST_ITEM_MARKER:
                # CommonMark 5.3: To interrupt a paragraph, the first list item must
                # have content. Check if the next token is paragraph content.
                saved_pos = self._pos
                self._advance()
                has_content = (
                    not self._at_end()
                    and self._current is not None
                    and self._current.type == TokenType.PARAGRAPH_LINE
                )
                # Restore position for further checks
                self._pos = saved_pos
                self._current = self._tokens[self._pos] if self._pos < len(self._tokens) else None

                if not has_content:
                    # Empty list item cannot interrupt paragraph - treat marker as text
                    lines.append(token.value.lstrip())
                    self._advance()
                    continue

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
            elif token.type == TokenType.LINK_REFERENCE_DEF:
                # CommonMark: Link reference definitions cannot interrupt paragraphs.
                # Treat as paragraph continuation text.
                line_start = token.location.offset
                line_end = token.location.end_offset
                original_line = self._source[line_start:line_end].rstrip("\n")
                lines.append(original_line.lstrip())
                self._advance()
            else:
                break

        # Check for setext heading: text followed by === or ---
        # CommonMark: setext underline can have up to 3 spaces indent, not 4+
        if len(lines) >= 2 and not last_line_was_indented_code:
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
        # CommonMark: A sequence of only --- (with optional trailing spaces) after
        # paragraph is setext heading, not thematic break. But "--- -" is a thematic break.
        if len(lines) >= 1 and not self._at_end():
            token = self._current
            if token is not None and token.type == TokenType.THEMATIC_BREAK:
                # Check if the thematic break is a valid setext underline
                # (only dashes, no other characters except trailing spaces)
                break_value = token.value.strip()
                if break_value and all(c == "-" for c in break_value):
                    self._advance()  # Consume the thematic break
                    # CommonMark: strip trailing whitespace from each line
                    heading_lines = [line.rstrip() for line in lines]
                    heading_text = "\n".join(heading_lines)
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
