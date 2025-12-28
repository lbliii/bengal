"""Recursive descent parser producing typed AST.

Consumes token stream from Lexer and builds typed AST nodes.
Produces immutable (frozen) dataclass nodes for thread-safety.

Thread Safety:
    Parser produces immutable AST (frozen dataclasses).
    Safe to share AST across threads.
"""

from __future__ import annotations

from collections.abc import Sequence

from bengal.rendering.parsers.patitas.lexer import Lexer
from bengal.rendering.parsers.patitas.location import SourceLocation
from bengal.rendering.parsers.patitas.nodes import (
    Block,
    BlockQuote,
    CodeSpan,
    Emphasis,
    FencedCode,
    Heading,
    HtmlInline,
    Image,
    IndentedCode,
    Inline,
    LineBreak,
    Link,
    List,
    ListItem,
    Paragraph,
    SoftBreak,
    Strong,
    Text,
    ThematicBreak,
)
from bengal.rendering.parsers.patitas.tokens import Token, TokenType


class Parser:
    """Recursive descent parser for Markdown.

    Consumes tokens from Lexer and builds typed AST.

    Usage:
        >>> parser = Parser("# Hello\\n\\nWorld")
        >>> ast = parser.parse()
        >>> ast[0]
        Heading(level=1, children=(Text(content='Hello'),), ...)

    Thread Safety:
        Produces immutable AST (frozen dataclasses).
        Safe to share AST across threads.
    """

    __slots__ = ("_source", "_tokens", "_pos", "_current", "_source_file")

    def __init__(self, source: str, source_file: str | None = None) -> None:
        """Initialize parser with source text.

        Args:
            source: Markdown source text
            source_file: Optional source file path for error messages
        """
        self._source = source
        self._source_file = source_file
        self._tokens: list[Token] = []
        self._pos = 0
        self._current: Token | None = None

    def parse(self) -> Sequence[Block]:
        """Parse source into AST blocks.

        Returns:
            Sequence of Block nodes

        Thread Safety:
            Returns immutable AST (frozen dataclasses).
        """
        # Tokenize source
        lexer = Lexer(self._source, self._source_file)
        self._tokens = list(lexer.tokenize())
        self._pos = 0
        self._current = self._tokens[0] if self._tokens else None

        # Parse blocks
        blocks: list[Block] = []
        while not self._at_end():
            block = self._parse_block()
            if block is not None:
                blocks.append(block)

        return tuple(blocks)

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

        content = value[pos:]

        # Parse inline content
        children = self._parse_inline(content, token.location)

        return Heading(
            location=token.location,
            level=level,  # type: ignore[arg-type]
            children=children,
            style="atx",
        )

    def _parse_fenced_code(self) -> FencedCode:
        """Parse fenced code block."""
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
            info = info_str

        # Collect content
        content_parts: list[str] = []
        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.FENCED_CODE_END:
                self._advance()
                break
            elif token.type == TokenType.FENCED_CODE_CONTENT:
                content_parts.append(token.value)
                self._advance()
            else:
                # Unexpected token, stop
                break

        code = "".join(content_parts)
        # Remove trailing newline if present
        if code.endswith("\n"):
            code = code[:-1]

        return FencedCode(
            location=start_token.location,
            code=code,
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
                content_lines.append(token.value)
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

    def _parse_list(self) -> List:
        """Parse list (unordered or ordered)."""
        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.LIST_ITEM_MARKER

        items: list[ListItem] = []
        ordered = start_token.value[0].isdigit()
        start = 1

        if ordered:
            # Extract starting number
            num_str = ""
            for c in start_token.value:
                if c.isdigit():
                    num_str += c
                else:
                    break
            if num_str:
                start = int(num_str)

        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type != TokenType.LIST_ITEM_MARKER:
                break

            # Check if same list type
            is_ordered = token.value[0].isdigit()
            if is_ordered != ordered:
                break

            self._advance()

            # Collect item content
            content_lines: list[str] = []
            while not self._at_end():
                tok = self._current
                assert tok is not None

                if tok.type == TokenType.PARAGRAPH_LINE:
                    content_lines.append(tok.value)
                    self._advance()
                elif tok.type == TokenType.BLANK_LINE:
                    self._advance()
                    break
                elif tok.type == TokenType.LIST_ITEM_MARKER:
                    break
                else:
                    break

            # Create item
            content = "\n".join(content_lines)
            if content:
                children = self._parse_inline(content, token.location)
                para = Paragraph(location=token.location, children=children)
                item = ListItem(location=token.location, children=(para,))
            else:
                item = ListItem(location=token.location, children=())

            items.append(item)

        return List(
            location=start_token.location,
            items=tuple(items),
            ordered=ordered,
            start=start,
            tight=True,  # TODO: detect loose lists
        )

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
        # Remove trailing newline
        if code.endswith("\n"):
            code = code[:-1]

        return IndentedCode(location=start_token.location, code=code)

    def _parse_paragraph(self) -> Paragraph:
        """Parse paragraph (consecutive text lines)."""
        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.PARAGRAPH_LINE

        lines: list[str] = []

        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.PARAGRAPH_LINE:
                lines.append(token.value)
                self._advance()
            else:
                break

        content = "\n".join(lines)
        children = self._parse_inline(content, start_token.location)

        return Paragraph(location=start_token.location, children=children)

    # =========================================================================
    # Inline parsing
    # =========================================================================

    def _parse_inline(self, text: str, location: SourceLocation) -> tuple[Inline, ...]:
        """Parse inline content from text.

        Handles emphasis, strong, links, images, code spans, etc.
        """
        if not text:
            return ()

        result: list[Inline] = []
        pos = 0
        text_start = 0

        while pos < len(text):
            char = text[pos]

            # Check for emphasis/strong: * or _
            if char in "*_":
                # Flush pending text
                if pos > text_start:
                    result.append(Text(location=location, content=text[text_start:pos]))

                # Count delimiter chars
                delim = char
                count = 0
                while pos < len(text) and text[pos] == delim:
                    count += 1
                    pos += 1

                # Try to find closing delimiter
                close_pos = self._find_closing_delimiter(text, pos, delim, count)

                if close_pos is not None:
                    inner = text[pos:close_pos]

                    if count >= 2:
                        # Strong (or strong + emphasis)
                        inner_children = self._parse_inline(inner, location)
                        node: Inline = Strong(location=location, children=inner_children)
                        if count > 2:
                            # Strong + emphasis
                            node = Emphasis(location=location, children=(node,))
                        result.append(node)
                    else:
                        # Emphasis
                        inner_children = self._parse_inline(inner, location)
                        result.append(Emphasis(location=location, children=inner_children))

                    pos = close_pos + count
                    text_start = pos
                else:
                    # No closing, treat as literal
                    result.append(Text(location=location, content=delim * count))
                    text_start = pos
                continue

            # Code span: `code`
            if char == "`":
                if pos > text_start:
                    result.append(Text(location=location, content=text[text_start:pos]))

                # Count backticks
                count = 0
                while pos < len(text) and text[pos] == "`":
                    count += 1
                    pos += 1

                # Find closing
                close_pos = text.find("`" * count, pos)
                if close_pos != -1:
                    code = text[pos:close_pos]
                    # Normalize spaces
                    if code.startswith(" ") and code.endswith(" ") and len(code) > 1:
                        code = code[1:-1]
                    result.append(CodeSpan(location=location, code=code))
                    pos = close_pos + count
                    text_start = pos
                else:
                    result.append(Text(location=location, content="`" * count))
                    text_start = pos
                continue

            # Link: [text](url) or [text][ref]
            if char == "[":
                link_result = self._try_parse_link(text, pos, location)
                if link_result:
                    if pos > text_start:
                        result.append(Text(location=location, content=text[text_start:pos]))
                    node, new_pos = link_result
                    result.append(node)
                    pos = new_pos
                    text_start = pos
                    continue

            # Image: ![alt](url)
            if char == "!" and pos + 1 < len(text) and text[pos + 1] == "[":
                img_result = self._try_parse_image(text, pos, location)
                if img_result:
                    if pos > text_start:
                        result.append(Text(location=location, content=text[text_start:pos]))
                    node, new_pos = img_result
                    result.append(node)
                    pos = new_pos
                    text_start = pos
                    continue

            # Hard break: \ at end of line
            if char == "\\" and pos + 1 < len(text) and text[pos + 1] == "\n":
                if pos > text_start:
                    result.append(Text(location=location, content=text[text_start:pos]))
                result.append(LineBreak(location=location))
                pos += 2
                text_start = pos
                continue

            # Soft break: single newline
            if char == "\n":
                if pos > text_start:
                    result.append(Text(location=location, content=text[text_start:pos]))
                result.append(SoftBreak(location=location))
                pos += 1
                text_start = pos
                continue

            # Escaped character
            if char == "\\" and pos + 1 < len(text):
                next_char = text[pos + 1]
                if next_char in "\\`*_{}[]()#+-.!|":
                    if pos > text_start:
                        result.append(Text(location=location, content=text[text_start:pos]))
                    result.append(Text(location=location, content=next_char))
                    pos += 2
                    text_start = pos
                    continue

            # HTML inline: < ... >
            if char == "<":
                html_result = self._try_parse_html_inline(text, pos, location)
                if html_result:
                    if pos > text_start:
                        result.append(Text(location=location, content=text[text_start:pos]))
                    node, new_pos = html_result
                    result.append(node)
                    pos = new_pos
                    text_start = pos
                    continue

            pos += 1

        # Flush remaining text
        if text_start < len(text):
            result.append(Text(location=location, content=text[text_start:]))

        return tuple(result)

    def _find_closing_delimiter(self, text: str, start: int, delim: str, count: int) -> int | None:
        """Find closing delimiter for emphasis/strong.

        Returns position of closing delimiter or None if not found.
        """
        pos = start
        while pos < len(text):
            if text[pos] == delim:
                # Count consecutive delimiters
                close_count = 0
                close_start = pos
                while pos < len(text) and text[pos] == delim:
                    close_count += 1
                    pos += 1

                if close_count >= count:
                    return close_start

            elif text[pos] == "`":
                # Skip code spans
                count_bt = 0
                while pos < len(text) and text[pos] == "`":
                    count_bt += 1
                    pos += 1
                # Find closing
                close = text.find("`" * count_bt, pos)
                if close != -1:
                    pos = close + count_bt
            else:
                pos += 1

        return None

    def _try_parse_link(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Link, int] | None:
        """Try to parse a link at position.

        Returns (Link, new_position) or None if not a link.
        """
        if text[pos] != "[":
            return None

        # Find ]
        bracket_pos = text.find("]", pos + 1)
        if bracket_pos == -1:
            return None

        link_text = text[pos + 1 : bracket_pos]

        # Check for (url) or [ref]
        if bracket_pos + 1 < len(text):
            next_char = text[bracket_pos + 1]

            if next_char == "(":
                # Inline link
                close_paren = text.find(")", bracket_pos + 2)
                if close_paren != -1:
                    dest = text[bracket_pos + 2 : close_paren]
                    url = dest.strip()
                    title = None

                    # Check for title
                    if " " in dest or "\t" in dest:
                        parts = dest.split(None, 1)
                        if len(parts) == 2:
                            url = parts[0]
                            title_part = parts[1].strip()
                            if (title_part.startswith('"') and title_part.endswith('"')) or (
                                title_part.startswith("'") and title_part.endswith("'")
                            ):
                                title = title_part[1:-1]

                    children = self._parse_inline(link_text, location)
                    return Link(
                        location=location, url=url, title=title, children=children
                    ), close_paren + 1

        return None

    def _try_parse_image(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Image, int] | None:
        """Try to parse an image at position.

        Returns (Image, new_position) or None if not an image.
        """
        if not (text[pos] == "!" and pos + 1 < len(text) and text[pos + 1] == "["):
            return None

        # Find ]
        bracket_pos = text.find("]", pos + 2)
        if bracket_pos == -1:
            return None

        alt_text = text[pos + 2 : bracket_pos]

        # Check for (url)
        if bracket_pos + 1 < len(text) and text[bracket_pos + 1] == "(":
            close_paren = text.find(")", bracket_pos + 2)
            if close_paren != -1:
                dest = text[bracket_pos + 2 : close_paren]
                url = dest.strip()
                title = None

                # Check for title
                if " " in dest or "\t" in dest:
                    parts = dest.split(None, 1)
                    if len(parts) == 2:
                        url = parts[0]
                        title_part = parts[1].strip()
                        if (title_part.startswith('"') and title_part.endswith('"')) or (
                            title_part.startswith("'") and title_part.endswith("'")
                        ):
                            title = title_part[1:-1]

                return Image(location=location, url=url, alt=alt_text, title=title), close_paren + 1

        return None

    def _try_parse_html_inline(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[HtmlInline, int] | None:
        """Try to parse inline HTML at position.

        Returns (HtmlInline, new_position) or None if not HTML.
        """
        if text[pos] != "<":
            return None

        # Look for closing >
        close_pos = text.find(">", pos + 1)
        if close_pos == -1:
            return None

        html = text[pos : close_pos + 1]

        # Basic validation: should look like HTML tag
        if len(html) < 3:
            return None

        inner = html[1:-1]
        if not inner:
            return None

        # Check if it's a tag (starts with letter or /)
        first = inner[0]
        if not (first.isalpha() or first == "/" or first == "!"):
            return None

        return HtmlInline(location=location, html=html), close_pos + 1

    # =========================================================================
    # Token navigation
    # =========================================================================

    def _at_end(self) -> bool:
        """Check if at end of token stream."""
        return self._current is None or self._current.type == TokenType.EOF

    def _advance(self) -> Token | None:
        """Advance to next token and return it."""
        self._pos += 1
        if self._pos < len(self._tokens):
            self._current = self._tokens[self._pos]
        else:
            self._current = None
        return self._current
