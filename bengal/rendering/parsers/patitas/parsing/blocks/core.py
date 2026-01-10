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

            case TokenType.FENCED_CODE_CONTENT:
                # Orphaned fenced code content (e.g., after block quote ended fenced code)
                # Treat as paragraph text
                return self._parse_orphaned_fence_content()

            case TokenType.FENCED_CODE_END:
                # Orphaned fence end marker - treat as new unclosed fenced code block
                return self._parse_orphaned_fence_end()

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

    def _parse_orphaned_fence_content(self) -> Paragraph:
        """Parse orphaned FENCED_CODE_CONTENT as paragraph.

        This happens when a fenced code block is interrupted (e.g., by block quote
        ending without >), leaving content tokens orphaned. Treat as paragraph text.
        """
        token = self._current
        assert token is not None and token.type == TokenType.FENCED_CODE_CONTENT

        # Collect consecutive content tokens as paragraph lines
        lines: list[str] = []
        while not self._at_end():
            current = self._current
            if current is None:
                break
            if current.type == TokenType.FENCED_CODE_CONTENT:
                lines.append(current.value.rstrip("\n"))
                self._advance()
            else:
                break

        content = "\n".join(lines)
        children = self._parse_inline(content, token.location)
        return Paragraph(location=token.location, children=children)

    def _parse_orphaned_fence_end(self) -> FencedCode:
        """Parse orphaned FENCED_CODE_END as new unclosed fenced code block.

        This happens when a fenced code block is interrupted, and the closing fence
        is now orphaned. In CommonMark, this becomes a new unclosed fenced code block.
        """
        token = self._current
        assert token is not None and token.type == TokenType.FENCED_CODE_END
        self._advance()

        # The token value is the fence chars (e.g., "```")
        fence_value = token.value.rstrip()
        marker = fence_value[0] if fence_value else "`"

        # Create an unclosed fenced code block (empty content)
        return FencedCode(
            location=token.location,
            source_start=0,
            source_end=0,
            info=None,
            marker=marker,  # type: ignore[arg-type]
            fence_indent=0,
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

        Algorithm:
        1. Consume the first BLOCK_QUOTE_MARKER
        2. Collect content, preserving nested > markers as content
        3. Handle lazy continuation (lines without > that continue paragraphs)
        4. Sub-parse the content for nested blocks
        """
        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.BLOCK_QUOTE_MARKER
        self._advance()

        # Collect content after the first > marker
        content_lines: list[str] = []
        current_line_parts: list[str] = []

        last_marker_line: int | None = start_token.location.lineno
        has_paragraph_content = False  # Track if we have paragraph content for lazy continuation
        has_lazy_continuation = False  # Track if any lazy continuation lines were included
        in_fenced_code = False  # Track if we're inside a fenced code block
        current_line_has_content = False  # Track if current line has content after > marker
        last_was_list_marker = False

        def flush_current_line() -> None:
            """Flush accumulated parts for current line."""
            nonlocal current_line_has_content
            nonlocal last_was_list_marker
            if current_line_parts:
                content_lines.append("".join(current_line_parts))
                current_line_parts.clear()
            elif not current_line_has_content and last_marker_line is not None:
                # Line only had > marker with no content - add empty line
                content_lines.append("")
            current_line_has_content = False
            last_was_list_marker = False

        while not self._at_end():
            token = self._current
            assert token is not None

            # If line changes, handle line transition
            if last_marker_line is not None and token.location.lineno != last_marker_line:
                # Check if the previous line was empty (just > with no content)
                if not current_line_has_content and not current_line_parts:
                    # Empty > line - add blank line and reset paragraph content flag
                    content_lines.append("")
                    has_paragraph_content = False
                flush_current_line()

                # Check for lazy continuation or end of block quote
                # CommonMark: Lazy continuation ONLY applies to paragraphs
                if token.type == TokenType.PARAGRAPH_LINE:
                    # Lazy continuation requires open paragraph, NOT code block
                    if not has_paragraph_content or in_fenced_code:
                        break
                    # This is a lazy continuation line (no > prefix)
                    has_lazy_continuation = True
                    content_lines.append(token.value.lstrip())
                    current_line_has_content = True  # Mark that we added content
                    last_marker_line = token.location.lineno
                    self._advance()
                    continue
                elif token.type == TokenType.INDENTED_CODE:
                    # Lazy continuation requires open paragraph, NOT code block
                    if not has_paragraph_content or in_fenced_code:
                        break
                    # This is a lazy continuation line with 4+ spaces
                    # Preserve the 4-space indent so sub-parser sees it as indented
                    has_lazy_continuation = True
                    content_lines.append("    " + token.value.rstrip("\n"))
                    current_line_has_content = True  # Mark that we added content
                    last_marker_line = token.location.lineno
                    self._advance()
                    continue
                elif token.type == TokenType.BLOCK_QUOTE_MARKER:
                    # New line with > marker - continue the block quote
                    last_marker_line = token.location.lineno
                    current_line_has_content = False  # Reset for new line
                    self._advance()
                    continue
                elif token.type == TokenType.BLANK_LINE:
                    # CommonMark: A blank line without > marker ends the blockquote.
                    break
                else:
                    # Any other token type ends the block quote
                    break

            # Handle tokens on the current line (same line as last marker)
            if token.type == TokenType.BLOCK_QUOTE_MARKER:
                # Nested > marker - include it in content for sub-parsing
                current_line_parts.append("> ")
                current_line_has_content = True
                last_marker_line = token.location.lineno
                self._advance()
            elif token.type == TokenType.FENCED_CODE_START:
                # Fenced code in block quote
                value = token.value
                if value.startswith("I") and ":" in value:
                    fence_part = value.split(":", 1)[1]
                else:
                    fence_part = value
                current_line_parts.append(fence_part)
                in_fenced_code = True
                has_paragraph_content = False
                current_line_has_content = True
                last_marker_line = token.location.lineno
                self._advance()
            elif token.type == TokenType.FENCED_CODE_END:
                # Closing fence
                current_line_parts.append(token.value.rstrip("\n"))
                in_fenced_code = False
                current_line_has_content = True
                last_marker_line = token.location.lineno
                self._advance()
            elif token.type == TokenType.FENCED_CODE_CONTENT:
                # Fenced code content
                current_line_parts.append(token.value.rstrip("\n"))
                current_line_has_content = True
                last_marker_line = token.location.lineno
                self._advance()
            elif token.type == TokenType.LINK_REFERENCE_DEF:
                # Link reference definitions inside block quotes are document-level metadata.
                # Do not include them in the rendered blockquote content to avoid recursive
                # block quote re-parsing (example 218).
                current_line_parts.clear()
                has_paragraph_content = False
                current_line_has_content = False
                last_marker_line = token.location.lineno
                self._advance()
            elif token.type in (
                TokenType.ATX_HEADING,
                TokenType.PARAGRAPH_LINE,
                TokenType.THEMATIC_BREAK,
                TokenType.LIST_ITEM_MARKER,
            ):
                # Block content - use token.value
                line_value = token.value.rstrip("\n")
                if token.type == TokenType.LIST_ITEM_MARKER:
                    # Normalize leading spaces so nested lists inside block quotes
                    # aren't treated as indented code (CommonMark 259/260).
                    line_value = line_value.lstrip()
                    last_was_list_marker = True
                elif token.type == TokenType.PARAGRAPH_LINE and last_was_list_marker:
                    # Strip indentation immediately following a list marker on the same line
                    line_value = line_value.lstrip()
                current_line_parts.append(line_value)
                current_line_has_content = True

                # Update has_paragraph_content
                # Note: PARAGRAPH_LINE with 4+ leading spaces will become indented code
                # in sub-parser, so it's NOT paragraph content for lazy continuation
                if token.type in (TokenType.PARAGRAPH_LINE, TokenType.LIST_ITEM_MARKER):
                    content = token.value.rstrip("\n")
                    leading_spaces = len(content) - len(content.lstrip())
                    # 4+ leading spaces = indented code (not paragraph content)
                    has_paragraph_content = leading_spaces < 4
                else:
                    has_paragraph_content = False

                last_marker_line = token.location.lineno
                self._advance()
            elif token.type == TokenType.BLANK_LINE:
                # Blank line within blockquote (after > on same line - shouldn't happen)
                flush_current_line()
                content_lines.append("")
                has_paragraph_content = False
                current_line_has_content = False
                last_marker_line = token.location.lineno
                self._advance()
            else:
                # Other token types - just add as content
                current_line_parts.append(token.value.rstrip("\n"))
                has_paragraph_content = False
                current_line_has_content = True
                last_marker_line = token.location.lineno
                self._advance()

        flush_current_line()

        # Parse content as blocks using recursive sub-parser
        content = "\n".join(content_lines)
        if content.strip() or any(line == "" for line in content_lines):
            # Use sub-parser to parse nested block content
            children = self._parse_nested_content(
                content,
                start_token.location,
                # CommonMark: setext underlines cannot span container boundaries.
                # Disable setext when we included lazy continuation lines.
                allow_setext_headings=not has_lazy_continuation,
            )
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
                # Blank lines might continue indented code if followed by more code.
                # CommonMark: blank lines within indented code are preserved,
                # including any whitespace on those lines (beyond 4 chars).
                # Look ahead past ALL blank lines to find INDENTED_CODE.
                blank_lines: list[str] = []
                next_pos = self._pos
                while next_pos < len(self._tokens):
                    next_token = self._tokens[next_pos]
                    if next_token.type == TokenType.BLANK_LINE:
                        # Get original line content to preserve whitespace
                        # (blank lines with 4+ spaces should keep excess spaces)
                        line_start = self._source.rfind("\n", 0, next_token.location.offset) + 1
                        line_end = self._source.find("\n", next_token.location.offset)
                        if line_end == -1:
                            line_end = len(self._source)
                        original_line = self._source[line_start:line_end]
                        # If line has 4+ spaces, preserve the excess
                        if len(original_line) >= 4 and original_line.startswith("    "):
                            blank_lines.append(original_line[4:] + "\n")
                        else:
                            blank_lines.append("\n")
                        next_pos += 1
                    elif next_token.type == TokenType.INDENTED_CODE:
                        # Found more code after blank lines - include blanks
                        content_parts.extend(blank_lines)
                        # Skip past the blank lines
                        for _ in range(len(blank_lines)):
                            self._advance()
                        break
                    else:
                        break
                else:
                    # End of tokens
                    break
                # If we didn't find more INDENTED_CODE, exit
                if (
                    next_pos >= len(self._tokens)
                    or self._tokens[next_pos].type != TokenType.INDENTED_CODE
                ):
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
        pending_setext_underline: str | None = None
        # Track if the last line came from INDENTED_CODE (4+ spaces indent)
        # Such lines cannot be setext underlines
        last_line_was_indented_code = False
        allow_setext = getattr(self, "_allow_setext_headings", True)

        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.PARAGRAPH_LINE:
                stripped_line = token.value.lstrip()
                if (
                    allow_setext
                    and lines
                    and not last_line_was_indented_code
                    and self._is_setext_underline(stripped_line)
                ):
                    pending_setext_underline = stripped_line
                    self._advance()
                    break
                lines.append(stripped_line)
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
                # CommonMark: link reference definitions cannot interrupt a paragraph.
                # If we're already inside a paragraph (lines collected), treat the
                # definition line as literal paragraph text. Otherwise, stop and let
                # the caller handle the definition.
                if lines:
                    line_start = token.location.offset
                    line_end = token.location.end_offset
                    original_line = self._source[line_start:line_end].rstrip("\n")
                    lines.append(original_line.lstrip())
                    self._advance()
                    continue
                break
            else:
                break

        # Check for setext heading: text followed by === or ---
        # CommonMark: setext underline can have up to 3 spaces indent, not 4+
        # Note: setext headings are disabled when parsing blockquote content with
        # lazy continuation lines (setext underlines can't span container boundaries)
        underline_line = pending_setext_underline or (lines[-1].strip() if len(lines) >= 2 else "")
        if (
            allow_setext
            and len(lines) >= 1
            and underline_line
            and not last_line_was_indented_code
            and self._is_setext_underline(underline_line)
        ):
            # Determine heading level: === is h1, --- is h2
            level = 1 if underline_line[0] == "=" else 2
            # Heading text is everything except the underline
            # CommonMark: strip trailing whitespace from each line
            heading_lines = lines if pending_setext_underline else lines[:-1]
            heading_lines = [line.rstrip() for line in heading_lines]
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
        if allow_setext and len(lines) >= 1 and not self._at_end():
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
