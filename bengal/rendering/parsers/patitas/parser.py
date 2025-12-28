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
    Directive,
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
    Role,
    SoftBreak,
    Strong,
    Text,
    ThematicBreak,
)
from bengal.rendering.parsers.patitas.tokens import Token, TokenType

# Frozenset for O(1) special character lookup in inline parsing
_INLINE_SPECIAL_CHARS = frozenset("*_`[!\\\n<{")


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

            case TokenType.DIRECTIVE_OPEN:
                return self._parse_directive()

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

    def _parse_directive(self) -> Directive:
        """Parse directive block (:::{name} ... :::)."""
        start_token = self._current
        assert start_token is not None and start_token.type == TokenType.DIRECTIVE_OPEN
        self._advance()

        # Get directive name
        name = ""
        if self._current and self._current.type == TokenType.DIRECTIVE_NAME:
            name = self._current.value
            self._advance()

        # Get optional title
        title: str | None = None
        if self._current and self._current.type == TokenType.DIRECTIVE_TITLE:
            title = self._current.value
            self._advance()

        # Parse options
        options: dict[str, str] = {}
        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.DIRECTIVE_OPTION:
                # Parse key:value from token
                if ":" in token.value:
                    key, value = token.value.split(":", 1)
                    options[key.strip()] = value.strip()
                self._advance()
            elif token.type == TokenType.BLANK_LINE:
                # Skip blank lines in option section
                self._advance()
                break  # Options section ends at first blank line
            else:
                break

        # Parse content (nested blocks)
        children: list[Block] = []
        while not self._at_end():
            token = self._current
            assert token is not None

            if token.type == TokenType.DIRECTIVE_CLOSE:
                self._advance()
                break
            elif token.type == TokenType.BLANK_LINE:
                self._advance()
                continue

            block = self._parse_block()
            if block is not None:
                children.append(block)

        return Directive(
            location=start_token.location,
            name=name,
            title=title,
            options=frozenset(options.items()),
            children=tuple(children),
        )

    # =========================================================================
    # Inline parsing with CommonMark delimiter stack algorithm
    # =========================================================================

    def _parse_inline(self, text: str, location: SourceLocation) -> tuple[Inline, ...]:
        """Parse inline content using CommonMark delimiter stack algorithm.

        This implements the proper flanking delimiter rules for emphasis/strong.
        See: https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis
        """
        if not text:
            return ()

        # Phase 1: Tokenize into text segments and delimiter runs
        tokens = self._tokenize_inline(text, location)

        # Phase 2: Process delimiter stack to match openers/closers
        self._process_emphasis(tokens)

        # Phase 3: Build AST from processed tokens
        return self._build_inline_ast(tokens, location)

    def _tokenize_inline(self, text: str, location: SourceLocation) -> list[dict]:
        """Tokenize inline content into segments and delimiters.

        Returns list of token dicts with type, content, position info.
        """
        tokens: list[dict] = []
        pos = 0
        text_len = len(text)  # Cache length for hot loop
        tokens_append = tokens.append  # Local reference for speed

        while pos < text_len:
            char = text[pos]

            # Code span: `code` - handle first to avoid delimiter confusion
            if char == "`":
                count = 0
                while pos < text_len and text[pos] == "`":
                    count += 1
                    pos += 1

                # Find closing backticks
                close_pos = self._find_code_span_close(text, pos, count)
                if close_pos != -1:
                    code = text[pos:close_pos]
                    # Normalize: strip one space from each end if both present
                    code_len = len(code)
                    if code_len >= 2 and code[0] == " " and code[-1] == " ":
                        # But not if it's all spaces
                        if code.strip():
                            code = code[1:-1]
                    tokens_append({"type": "code_span", "code": code})
                    pos = close_pos + count
                else:
                    tokens_append({"type": "text", "content": "`" * count})
                continue

            # Emphasis delimiters: * or _
            if char in "*_":
                delim_start = pos
                delim_char = char
                count = 0
                while pos < text_len and text[pos] == delim_char:
                    count += 1
                    pos += 1

                # Determine flanking status (CommonMark rules)
                before = text[delim_start - 1] if delim_start > 0 else " "
                after = text[pos] if pos < text_len else " "

                left_flanking = self._is_left_flanking(before, after, delim_char)
                right_flanking = self._is_right_flanking(before, after, delim_char)

                # For underscore, additional rules apply
                if delim_char == "_":
                    can_open = left_flanking and (
                        not right_flanking or self._is_punctuation(before)
                    )
                    can_close = right_flanking and (
                        not left_flanking or self._is_punctuation(after)
                    )
                else:
                    can_open = left_flanking
                    can_close = right_flanking

                tokens_append(
                    {
                        "type": "delimiter",
                        "char": delim_char,
                        "count": count,
                        "original_count": count,
                        "can_open": can_open,
                        "can_close": can_close,
                        "active": True,
                    }
                )
                continue

            # Link: [text](url)
            if char == "[":
                link_result = self._try_parse_link(text, pos, location)
                if link_result:
                    node, new_pos = link_result
                    tokens_append({"type": "node", "node": node})
                    pos = new_pos
                    continue
                tokens_append({"type": "text", "content": "["})
                pos += 1
                continue

            # Image: ![alt](url)
            if char == "!":
                if pos + 1 < text_len and text[pos + 1] == "[":
                    img_result = self._try_parse_image(text, pos, location)
                    if img_result:
                        node, new_pos = img_result
                        tokens_append({"type": "node", "node": node})
                        pos = new_pos
                        continue
                # Not an image, emit ! as literal text
                tokens_append({"type": "text", "content": "!"})
                pos += 1
                continue

            # Hard break: \ at end of line
            if char == "\\" and pos + 1 < text_len and text[pos + 1] == "\n":
                tokens_append({"type": "hard_break"})
                pos += 2
                continue

            # Soft break: single newline
            if char == "\n":
                tokens_append({"type": "soft_break"})
                pos += 1
                continue

            # Escaped character
            if char == "\\":
                if pos + 1 < text_len:
                    next_char = text[pos + 1]
                    if next_char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~":
                        # CommonMark: any ASCII punctuation can be escaped
                        tokens_append({"type": "text", "content": next_char})
                        pos += 2
                        continue
                    else:
                        # Backslash before non-punctuation: emit literal backslash
                        tokens_append({"type": "text", "content": "\\"})
                        pos += 1
                        continue
                else:
                    # Backslash at end of text: emit literal backslash
                    tokens_append({"type": "text", "content": "\\"})
                    pos += 1
                    continue

            # HTML inline: <tag>
            if char == "<":
                html_result = self._try_parse_html_inline(text, pos, location)
                if html_result:
                    node, new_pos = html_result
                    tokens_append({"type": "node", "node": node})
                    pos = new_pos
                    continue
                else:
                    # Not valid HTML, emit < as literal text
                    tokens_append({"type": "text", "content": "<"})
                    pos += 1
                    continue

            # Role: {role}`content`
            if char == "{":
                role_result = self._try_parse_role(text, pos, location)
                if role_result:
                    node, new_pos = role_result
                    tokens_append({"type": "node", "node": node})
                    pos = new_pos
                    continue
                else:
                    # Not a valid role, emit { as literal text
                    tokens_append({"type": "text", "content": "{"})
                    pos += 1
                    continue

            # Regular text - accumulate using set lookup (O(1) per char)
            text_start = pos
            # Use a frozenset for faster membership testing
            while pos < text_len and text[pos] not in _INLINE_SPECIAL_CHARS:
                pos += 1
            if pos > text_start:
                tokens_append({"type": "text", "content": text[text_start:pos]})

        return tokens

    def _is_left_flanking(self, before: str, after: str, delim: str) -> bool:
        """Check if delimiter run is left-flanking.

        Left-flanking: not followed by whitespace, and either:
        - not followed by punctuation, OR
        - preceded by whitespace or punctuation
        """
        if self._is_whitespace(after):
            return False
        if not self._is_punctuation(after):
            return True
        return self._is_whitespace(before) or self._is_punctuation(before)

    def _is_right_flanking(self, before: str, after: str, delim: str) -> bool:
        """Check if delimiter run is right-flanking.

        Right-flanking: not preceded by whitespace, and either:
        - not preceded by punctuation, OR
        - followed by whitespace or punctuation
        """
        if self._is_whitespace(before):
            return False
        if not self._is_punctuation(before):
            return True
        return self._is_whitespace(after) or self._is_punctuation(after)

    def _is_whitespace(self, char: str) -> bool:
        """Check if character is Unicode whitespace."""
        return char in " \t\n\r\f\v" or char == ""

    def _is_punctuation(self, char: str) -> bool:
        """Check if character is ASCII punctuation."""
        return char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"

    def _find_code_span_close(self, text: str, start: int, backtick_count: int) -> int:
        """Find closing backticks for code span."""
        pos = start
        text_len = len(text)
        while True:
            idx = text.find("`", pos)
            if idx == -1:
                return -1
            # Count consecutive backticks
            count = 0
            check_pos = idx
            while check_pos < text_len and text[check_pos] == "`":
                count += 1
                check_pos += 1
            if count == backtick_count:
                return idx
            pos = check_pos

    def _process_emphasis(self, tokens: list[dict]) -> None:
        """Process delimiter stack to match emphasis openers/closers.

        Implements CommonMark emphasis algorithm.
        Modifies tokens in place to mark matched delimiters.
        """
        # Find delimiter tokens that can close
        closer_idx = 0
        while closer_idx < len(tokens):
            closer = tokens[closer_idx]
            if (
                closer.get("type") != "delimiter"
                or not closer.get("can_close")
                or not closer.get("active")
            ):
                closer_idx += 1
                continue

            # Look backwards for matching opener
            opener_idx = closer_idx - 1
            found_opener = False

            while opener_idx >= 0:
                opener = tokens[opener_idx]
                if opener.get("type") != "delimiter":
                    opener_idx -= 1
                    continue
                if not opener.get("can_open") or not opener.get("active"):
                    opener_idx -= 1
                    continue
                if opener.get("char") != closer.get("char"):
                    opener_idx -= 1
                    continue

                # Check "sum of delimiters" rule (CommonMark)
                # If either opener or closer can both open and close,
                # the sum of delimiter counts must not be multiple of 3
                if (opener.get("can_open") and opener.get("can_close")) or (
                    closer.get("can_open") and closer.get("can_close")
                ):
                    if (opener["count"] + closer["count"]) % 3 == 0:
                        if opener["count"] % 3 != 0 or closer["count"] % 3 != 0:
                            opener_idx -= 1
                            continue

                # Found matching opener
                found_opener = True

                # Determine how many delimiters to use
                use_count = 2 if (opener["count"] >= 2 and closer["count"] >= 2) else 1

                # Mark the match
                opener["matched_with"] = closer_idx
                opener["match_count"] = use_count
                closer["matched_with"] = opener_idx
                closer["match_count"] = use_count

                # Consume delimiters
                opener["count"] -= use_count
                closer["count"] -= use_count

                # Deactivate if exhausted
                if opener["count"] == 0:
                    opener["active"] = False
                if closer["count"] == 0:
                    closer["active"] = False

                # Remove any unmatched delimiters between opener and closer
                for i in range(opener_idx + 1, closer_idx):
                    if tokens[i].get("type") == "delimiter" and tokens[i].get("active"):
                        tokens[i]["active"] = False

                break

            if not found_opener:
                # No opener found, deactivate closer if it can't open
                if not closer.get("can_open"):
                    closer["active"] = False
                closer_idx += 1
            elif closer["count"] > 0:
                # Closer still has delimiters, continue from same position
                pass
            else:
                closer_idx += 1

    def _build_inline_ast(self, tokens: list[dict], location: SourceLocation) -> tuple[Inline, ...]:
        """Build AST from processed tokens."""
        result: list[Inline] = []
        idx = 0

        while idx < len(tokens):
            token = tokens[idx]
            token_type = token.get("type")

            if token_type == "text":
                result.append(Text(location=location, content=token["content"]))
                idx += 1

            elif token_type == "code_span":
                result.append(CodeSpan(location=location, code=token["code"]))
                idx += 1

            elif token_type == "node":
                result.append(token["node"])
                idx += 1

            elif token_type == "hard_break":
                result.append(LineBreak(location=location))
                idx += 1

            elif token_type == "soft_break":
                result.append(SoftBreak(location=location))
                idx += 1

            elif token_type == "delimiter":
                if "matched_with" in token and token["matched_with"] > idx:
                    # This is an opener - build emphasis/strong
                    closer_idx = token["matched_with"]
                    match_count = token["match_count"]

                    # Collect children between opener and closer
                    children = self._build_inline_ast(tokens[idx + 1 : closer_idx], location)

                    # Build node
                    if match_count == 2:
                        node: Inline = Strong(location=location, children=children)
                    else:
                        node = Emphasis(location=location, children=children)

                    result.append(node)

                    # Skip to after closer
                    idx = closer_idx + 1
                else:
                    # Unmatched delimiter - emit as text
                    count = token.get("original_count", token.get("count", 1))
                    if token.get("active") and token.get("count", 0) > 0:
                        count = token["count"]
                    result.append(Text(location=location, content=token["char"] * count))
                    idx += 1

            else:
                idx += 1

        return tuple(result)

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

    def _try_parse_role(
        self, text: str, pos: int, location: SourceLocation
    ) -> tuple[Role, int] | None:
        """Try to parse a role at position.

        Syntax: {role}`content`

        Returns (Role, new_position) or None if not a role.
        """
        if text[pos] != "{":
            return None

        # Find closing }
        brace_close = text.find("}", pos + 1)
        if brace_close == -1:
            return None

        role_name = text[pos + 1 : brace_close].strip()

        # Validate role name (alphanumeric + - + _)
        if not role_name or not all(c.isalnum() or c in "-_" for c in role_name):
            return None

        # Must have backtick immediately after }
        if brace_close + 1 >= len(text) or text[brace_close + 1] != "`":
            return None

        # Find closing backtick
        content_start = brace_close + 2
        backtick_close = text.find("`", content_start)
        if backtick_close == -1:
            return None

        content = text[content_start:backtick_close]

        return Role(
            location=location,
            name=role_name,
            content=content,
        ), backtick_close + 1

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
