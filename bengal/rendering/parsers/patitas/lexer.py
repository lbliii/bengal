"""State-machine lexer with O(n) guaranteed performance.

Implements a window-based approach: scan entire lines, classify, then commit.
This eliminates position rewinds and guarantees forward progress.

No regex in the hot path. Zero ReDoS vulnerability by construction.

Thread Safety:
    Lexer instances are single-use. Create one per source string.
    All state is instance-local; no shared mutable state.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from enum import Enum, auto
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.location import SourceLocation
from bengal.rendering.parsers.patitas.parsing.charsets import (
    FENCE_CHARS,
    THEMATIC_BREAK_CHARS,
    UNORDERED_LIST_MARKERS,
)
from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    pass


class LexerMode(Enum):
    """Lexer operating modes.

    The lexer switches between modes based on context:
    - BLOCK: Between blocks, scanning for block starts
    - CODE_FENCE: Inside fenced code block
    - DIRECTIVE: Inside directive block
    - HTML_BLOCK: Inside HTML block (types 1-7)
    """

    BLOCK = auto()  # Between blocks
    CODE_FENCE = auto()  # Inside fenced code block
    DIRECTIVE = auto()  # Inside directive block
    HTML_BLOCK = auto()  # Inside HTML block


# CommonMark HTML block type 1 tags (case-insensitive)
_HTML_BLOCK_TYPE1_TAGS = frozenset({"pre", "script", "style", "textarea"})

# CommonMark HTML block type 6 tags (case-insensitive)
# These are "block-level" HTML tags that end on blank line
_HTML_BLOCK_TYPE6_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "base",
        "basefont",
        "blockquote",
        "body",
        "caption",
        "center",
        "col",
        "colgroup",
        "dd",
        "details",
        "dialog",
        "dir",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "frame",
        "frameset",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "head",
        "header",
        "hr",
        "html",
        "iframe",
        "legend",
        "li",
        "link",
        "main",
        "menu",
        "menuitem",
        "nav",
        "noframes",
        "ol",
        "optgroup",
        "option",
        "p",
        "param",
        "search",
        "section",
        "summary",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "title",
        "tr",
        "track",
        "ul",
    }
)


class Lexer:
    """State-machine lexer with O(n) guaranteed performance.

    Uses a window-based approach for block scanning:
    1. Scan to end of line (find window)
    2. Classify the line (pure logic, no position changes)
    3. Commit position (always advances)

    This eliminates rewinds and guarantees forward progress.

    Usage:
        >>> lexer = Lexer("# Hello\\n\\nWorld")
        >>> for token in lexer.tokenize():
        ...     print(token)
        Token(ATX_HEADING, '# Hello', 1:1)
        Token(BLANK_LINE, '', 2:1)
        Token(PARAGRAPH_LINE, 'World', 3:1)
        Token(EOF, '', 3:6)

    Thread Safety:
        Lexer instances are single-use. Create one per source string.
        All state is instance-local; no shared mutable state.
    """

    __slots__ = (
        "_source",
        "_source_len",  # Cached len(source) to avoid repeated calls
        "_pos",
        "_lineno",
        "_col",
        "_mode",
        "_source_file",
        "_fence_char",
        "_fence_count",
        "_fence_info",  # Language hint from fence start
        "_fence_indent",  # Leading spaces on opening fence for CommonMark stripping
        "_consumed_newline",
        "_saved_lineno",
        "_saved_col",
        # Directive state
        "_directive_stack",  # Stack of (colon_count, name) for nested directives
        # Transformation
        "_text_transformer",
        # HTML block state
        "_html_block_type",  # 1-7 per CommonMark spec
        "_html_block_content",  # Accumulated HTML content
        "_html_block_start",  # Start position for location
    )

    def __init__(
        self,
        source: str,
        source_file: str | None = None,
        text_transformer: Callable[[str], str] | None = None,
    ) -> None:
        """Initialize lexer with source text.

        Args:
            source: Markdown source text
            source_file: Optional source file path for error messages
            text_transformer: Optional callback to transform plain text lines
        """
        self._source = source
        self._source_len = len(source)  # Cache length
        self._pos = 0
        self._lineno = 1
        self._col = 1
        self._mode = LexerMode.BLOCK
        self._source_file = source_file
        self._text_transformer = text_transformer
        self._fence_char = ""
        self._fence_count = 0
        self._fence_info = ""
        self._fence_indent = 0  # Leading spaces on opening fence
        self._consumed_newline = False
        self._saved_lineno = 1
        self._saved_col = 1
        self._directive_stack = []

        # Fenced code state
        self._fence_char: str = ""
        self._fence_count: int = 0
        self._fence_indent: int = 0

        # HTML block state
        self._html_block_type: int = 0
        self._html_block_content: list[str] = []
        self._html_block_start: int = 0

        # Directive state: stack of (colon_count, name) for nested directives
        self._directive_stack: list[tuple[int, str]] = []

        # Line consumption tracking
        self._consumed_newline: bool = False

        # Saved location for efficient location tracking
        self._saved_lineno: int = 1
        self._saved_col: int = 1

    def tokenize(self) -> Iterator[Token]:
        """Tokenize source into token stream.

        Yields:
            Token objects one at a time

        Complexity: O(n) where n = len(source)
        Memory: O(1) iterator (tokens yielded, not accumulated)
        """
        source_len = self._source_len  # Local var for faster access
        while self._pos < source_len:
            yield from self._dispatch_mode()

        yield Token(TokenType.EOF, "", self._location())

    def _dispatch_mode(self) -> Iterator[Token]:
        """Dispatch to appropriate scanner based on current mode."""
        if self._mode == LexerMode.BLOCK:
            yield from self._scan_block()
        elif self._mode == LexerMode.CODE_FENCE:
            yield from self._scan_code_fence_content()
        elif self._mode == LexerMode.DIRECTIVE:
            yield from self._scan_directive_content()
        elif self._mode == LexerMode.HTML_BLOCK:
            yield from self._scan_html_block_content()

    # =========================================================================
    # Window-based block scanning
    # =========================================================================

    def _scan_block(self) -> Iterator[Token]:
        """Scan for block-level elements using window approach.

        Algorithm:
        1. Find end of current line (window)
        2. Classify the line content (pure logic)
        3. Emit token and commit position (always advances)
        """
        # Save location BEFORE scanning (for O(1) location tracking)
        self._save_location()

        line_start = self._pos
        line_end = self._find_line_end()
        line = self._source[line_start:line_end]

        # Calculate indent (spaces/tabs at start)
        indent, content_start = self._calc_indent(line)
        content = line[content_start:]

        # Apply text transformation (the "window thing")
        # This allows variables to resolve BEFORE classification, so {{ var }}
        # can contain block markers like headings or lists.
        if self._text_transformer:
            content = self._text_transformer(content)

        # Commit position now - we WILL consume this line
        self._commit_to(line_end)

        # Empty line or whitespace only = blank line
        if not content or content.isspace():
            yield Token(TokenType.BLANK_LINE, "", self._location_from(line_start))
            return

        # CommonMark: 4+ spaces indent creates an indented code block
        # This takes priority over most block types (except fenced code inside lists)
        # Must check BEFORE ATX headings, thematic breaks, and block quotes
        if indent >= 4:
            yield Token(
                TokenType.INDENTED_CODE,
                line[4:] + ("\n" if self._consumed_newline else ""),
                self._location_from(line_start),
            )
            return

        # Check for fenced code blocks
        # (fenced code can be indented inside list items, but indent < 4)
        # Fenced code: ``` or ~~~ (uses O(1) frozenset lookup)
        if content[0] in FENCE_CHARS:
            token = self._try_classify_fence_start(content, line_start, indent)
            if token:
                yield token
                return

        # HTML block: <tag>, <!--, <?, <!, </tag>, etc.
        # Must be checked before most other block types
        # CommonMark 4.6 defines 7 types of HTML blocks
        if content[0] == "<":
            html_result = self._try_classify_html_block_start(content, line_start, line)
            if html_result:
                yield from html_result
                return

        # ATX Heading: # ## ### etc.
        # CommonMark: ATX heading cannot be indented 4+ spaces (already handled above)
        if content.startswith("#"):
            token = self._try_classify_atx_heading(content, line_start)
            if token:
                yield token
                return

        # Block quote: > (cannot be indented 4+ spaces)
        if content.startswith(">"):
            yield from self._classify_block_quote(content, line_start)
            return

        # Thematic break: ---, ***, ___ (must check BEFORE list markers)
        # A line like "- - -" or "* * *" could be either, but thematic break takes precedence
        # Uses O(1) frozenset lookup
        if content[0] in THEMATIC_BREAK_CHARS:
            token = self._try_classify_thematic_break(content, line_start)
            if token:
                yield token
                return

        # List item: -, *, +, or 1. 1)
        # Pass indent so nested lists can be detected
        list_tokens = self._try_classify_list_marker(content, line_start, indent)
        if list_tokens is not None:
            yield from list_tokens
            return

        # Footnote definition: [^id]: content
        footnote_token = self._try_classify_footnote_def(content, line_start)
        if footnote_token is not None:
            yield footnote_token
            return

        # Link reference definition: [label]: url "title"
        if content.startswith("[") and not content.startswith("[^"):
            link_ref_token = self._try_classify_link_reference_def(content, line_start)
            if link_ref_token is not None:
                yield link_ref_token
                return

        # Directive: :::{name} or ::::{name} etc.
        if content.startswith(":"):
            directive_tokens = self._try_classify_directive_start(content, line_start)
            if directive_tokens is not None:
                yield from directive_tokens
                return

        # Default: paragraph line
        # Prefix with spaces to preserve indent (like list markers do)
        # This allows parser to detect non-indented paragraphs that terminate lists
        indented_content = " " * indent + content.rstrip("\n")
        yield Token(
            TokenType.PARAGRAPH_LINE,
            indented_content,
            self._location_from(line_start),
        )

    def _scan_code_fence_content(self) -> Iterator[Token]:
        """Scan content inside fenced code block using window approach."""
        # Save location BEFORE scanning (for O(1) location tracking)
        self._save_location()

        line_start = self._pos
        line_end = self._find_line_end()
        line = self._source[line_start:line_end]

        # Check for closing fence
        if self._is_closing_fence(line):
            self._commit_to(line_end)
            # Return to DIRECTIVE mode if inside a directive, otherwise BLOCK
            if self._directive_stack:
                self._mode = LexerMode.DIRECTIVE
            else:
                self._mode = LexerMode.BLOCK
            # Reset fence state
            fence_char = self._fence_char
            self._fence_char = ""
            self._fence_count = 0
            self._fence_info = ""
            self._fence_indent = 0
            yield Token(
                TokenType.FENCED_CODE_END,
                fence_char * 3,
                self._location_from(line_start),
            )
            return

        # Regular content line
        self._commit_to(line_end)

        # Include newline in content if we consumed one
        content = line
        if self._consumed_newline:
            content = line + "\n"

        yield Token(
            TokenType.FENCED_CODE_CONTENT,
            content,
            self._location_from(line_start),
        )

    def _handoff_to_delegate(self) -> Iterator[Token]:
        # REMOVED: In line with updated RFC, handoff happens in the Renderer.
        # This Lexer remains "dumb" and only emits offsets.
        pass

    def _find_closing_fence_pos(self) -> int:
        # REMOVED: No longer needed by Lexer.
        pass

    # =========================================================================
    # Line classification helpers (pure logic, no position mutation)
    # =========================================================================

    def _try_classify_atx_heading(self, content: str, line_start: int) -> Token | None:
        """Try to classify content as ATX heading.

        Returns Token if valid heading, None otherwise.
        """
        # Count leading #
        level = 0
        pos = 0
        while pos < len(content) and content[pos] == "#" and level < 6:
            level += 1
            pos += 1

        if level == 0:
            return None

        # Must be followed by space, tab, newline, or end
        if pos < len(content) and content[pos] not in " \t\n":
            return None

        # Skip space after #
        if pos < len(content) and content[pos] in " \t":
            pos += 1

        # Rest is heading content
        heading_content = content[pos:].rstrip("\n")

        # Remove trailing # sequence (if preceded by space)
        heading_content = heading_content.rstrip()
        if heading_content.endswith("#"):
            # Find where trailing #s start
            trailing_start = len(heading_content)
            while trailing_start > 0 and heading_content[trailing_start - 1] == "#":
                trailing_start -= 1
            # Must be preceded by space
            if trailing_start > 0 and heading_content[trailing_start - 1] in " \t":
                heading_content = heading_content[: trailing_start - 1].rstrip()
            elif trailing_start == 0:
                heading_content = ""

        value = "#" * level + (" " + heading_content if heading_content else "")
        return Token(TokenType.ATX_HEADING, value, self._location_from(line_start))

    def _try_classify_fence_start(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        """Try to classify content as fenced code start.

        Args:
            content: Line content with leading whitespace stripped
            line_start: Position in source where line starts
            indent: Number of leading spaces (for CommonMark indent stripping)

        Returns Token if valid fence, None otherwise.
        """
        if not content:
            return None

        fence_char = content[0]
        if fence_char not in "`~":
            return None

        # Count fence characters
        count = 0
        pos = 0
        while pos < len(content) and content[pos] == fence_char:
            count += 1
            pos += 1

        if count < 3:
            return None

        # Rest is info string (language hint)
        info = content[pos:].rstrip("\n").strip()

        # Backtick fences cannot have backticks in info string
        if fence_char == "`" and "`" in info:
            return None

        # Valid fence - update state
        self._fence_char = fence_char
        self._fence_count = count
        self._fence_info = info.split()[0] if info else ""
        self._fence_indent = indent  # Store indent for content stripping
        self._mode = LexerMode.CODE_FENCE

        # Encode indent in token value: "I{indent}:{fence}{info}"
        # Parser will extract this to set fence_indent on FencedCode node
        value = f"I{indent}:" + fence_char * count + (info if info else "")
        return Token(TokenType.FENCED_CODE_START, value, self._location_from(line_start))

    def _try_classify_thematic_break(self, content: str, line_start: int) -> Token | None:
        """Try to classify content as thematic break.

        Returns Token if valid break, None otherwise.
        """
        if not content:
            return None

        char = content[0]
        if char not in "-*_":
            return None

        # Count the marker characters (ignoring spaces/tabs)
        count = 0
        for c in content.rstrip("\n"):
            if c == char:
                count += 1
            elif c in " \t":
                continue
            else:
                # Invalid character
                return None

        if count >= 3:
            return Token(
                TokenType.THEMATIC_BREAK,
                char * 3,
                self._location_from(line_start),
            )

        return None

    def _classify_block_quote(self, content: str, line_start: int) -> Iterator[Token]:
        """Classify block quote marker and emit tokens."""
        # Yield the > marker
        yield Token(TokenType.BLOCK_QUOTE_MARKER, ">", self._location_from(line_start))

        # Content after > (skip optional space)
        pos = 1
        if pos < len(content) and content[pos] == " ":
            pos += 1

        remaining = content[pos:].rstrip("\n")
        if remaining:
            yield Token(
                TokenType.PARAGRAPH_LINE,
                remaining,
                self._location_from(line_start),
            )

    def _try_classify_html_block_start(
        self, content: str, line_start: int, full_line: str
    ) -> Iterator[Token] | None:
        """Try to classify content as HTML block start.

        CommonMark 4.6 defines 7 types of HTML blocks.

        Args:
            content: Line content with leading whitespace stripped
            line_start: Position in source where line starts
            full_line: The full line including leading whitespace

        Returns:
            Iterator yielding HTML_BLOCK token, or None if not HTML block.
        """
        if not content or content[0] != "<":
            return None

        content_lower = content.lower()

        # Include newline in full_line if we consumed one
        full_line_nl = full_line + ("\n" if self._consumed_newline else "")

        # Type 1: <pre, <script, <style, <textarea (case-insensitive)
        # Ends with </pre>, </script>, </style>, </textarea>
        for tag in _HTML_BLOCK_TYPE1_TAGS:
            if content_lower.startswith(f"<{tag}") and (
                len(content) == len(tag) + 1 or content[len(tag) + 1] in " \t\n>"
            ):
                self._html_block_type = 1
                self._html_block_content = [full_line_nl]
                self._html_block_start = line_start
                # Check if end condition on same line
                end_tag = f"</{tag}>"
                if end_tag in content_lower:
                    return self._emit_html_block()
                self._mode = LexerMode.HTML_BLOCK
                return iter([])  # Empty iterator, tokens come from scan

        # Type 2: <!-- (HTML comment)
        # Ends with -->
        if content.startswith("<!--"):
            self._html_block_type = 2
            self._html_block_content = [full_line_nl]
            self._html_block_start = line_start
            if "-->" in content[4:]:
                return self._emit_html_block()
            self._mode = LexerMode.HTML_BLOCK
            return iter([])

        # Type 3: <? (processing instruction)
        # Ends with ?>
        if content.startswith("<?"):
            self._html_block_type = 3
            self._html_block_content = [full_line]
            self._html_block_start = line_start
            if "?>" in content[2:]:
                return self._emit_html_block()
            self._mode = LexerMode.HTML_BLOCK
            return iter([])

        # Type 4: <! followed by uppercase letter (declaration)
        # Ends with >
        if len(content) >= 3 and content[1] == "!" and content[2].isupper():
            self._html_block_type = 4
            self._html_block_content = [full_line]
            self._html_block_start = line_start
            if ">" in content[2:]:
                return self._emit_html_block()
            self._mode = LexerMode.HTML_BLOCK
            return iter([])

        # Type 5: <![CDATA[
        # Ends with ]]>
        if content.startswith("<![CDATA["):
            self._html_block_type = 5
            self._html_block_content = [full_line]
            self._html_block_start = line_start
            if "]]>" in content[9:]:
                return self._emit_html_block()
            self._mode = LexerMode.HTML_BLOCK
            return iter([])

        # Type 6: <tagname or </tagname where tagname is block-level
        # Ends with blank line (or EOF)
        tag_match = self._extract_html_tag_name(content)
        if tag_match and tag_match.lower() in _HTML_BLOCK_TYPE6_TAGS:
            self._html_block_type = 6
            self._html_block_content = [full_line]
            self._html_block_start = line_start
            # If at EOF, emit immediately
            if self._pos >= self._source_len:
                return self._emit_html_block()
            self._mode = LexerMode.HTML_BLOCK
            return iter([])

        # Type 7: Complete open tag (not a type 6 tag) or closing tag
        # Must be the only thing on the line (possibly followed by whitespace)
        # Ends with blank line (or EOF)
        if self._is_complete_html_tag(content):
            self._html_block_type = 7
            self._html_block_content = [full_line]
            self._html_block_start = line_start
            # If at EOF, emit immediately
            if self._pos >= self._source_len:
                return self._emit_html_block()
            self._mode = LexerMode.HTML_BLOCK
            return iter([])

        return None

    def _extract_html_tag_name(self, content: str) -> str | None:
        """Extract tag name from HTML opening or closing tag."""
        if not content or content[0] != "<":
            return None

        pos = 1
        # Handle closing tag </
        if pos < len(content) and content[pos] == "/":
            pos += 1

        # Tag name must start with letter
        if pos >= len(content) or not content[pos].isalpha():
            return None

        start = pos
        while pos < len(content) and (content[pos].isalnum() or content[pos] == "-"):
            pos += 1

        return content[start:pos] if pos > start else None

    def _is_complete_html_tag(self, content: str) -> bool:
        """Check if content is a complete HTML open/close tag.

        Type 7 HTML blocks require a complete tag that's the only content on line.
        """
        content = content.rstrip()
        if not content or content[0] != "<":
            return False

        # Simple check: starts with <, ends with >, has valid tag structure
        if not content.endswith(">"):
            return False

        # Must have at least <x> (3 chars)
        if len(content) < 3:
            return False

        # Check for closing tag </x>
        if content[1] == "/":
            # Closing tag: must have letter after /
            if len(content) < 4:
                return False
            if not content[2].isalpha():
                return False
            # Check tag name is valid
            pos = 2
            while pos < len(content) - 1 and (content[pos].isalnum() or content[pos] == "-"):
                pos += 1
            # Must end with just > or whitespace then >
            rest = content[pos:-1]
            return rest.strip() == ""

        # Opening tag: <tagname ...>
        if not content[1].isalpha():
            return False

        # Check we have a valid tag name and structure
        pos = 1
        while pos < len(content) and (content[pos].isalnum() or content[pos] == "-"):
            pos += 1

        # Check it's a valid tag (has attributes or just ends)
        rest = content[pos:-1]  # Everything between tag name and >

        # Self-closing tags are valid
        if rest.endswith("/"):
            rest = rest[:-1]

        # The rest should be valid attributes or empty
        # For simplicity, just check it doesn't look like paragraph text
        return True

    def _emit_html_block(self) -> Iterator[Token]:
        """Emit accumulated HTML block as a single token."""
        # Content already has newlines at the end of each line
        html_content = "".join(self._html_block_content)
        if html_content and not html_content.endswith("\n"):
            html_content += "\n"

        yield Token(
            TokenType.HTML_BLOCK,
            html_content,
            self._location_from(self._html_block_start),
        )

        # Reset state
        self._html_block_type = 0
        self._html_block_content = []
        self._html_block_start = 0
        self._mode = LexerMode.BLOCK

    def _scan_html_block_content(self) -> Iterator[Token]:
        """Scan content inside HTML block until end condition."""
        self._save_location()

        line_start = self._pos
        line_end = self._find_line_end()
        line = self._source[line_start:line_end]

        self._commit_to(line_end)

        # Add line to content
        if self._consumed_newline:
            self._html_block_content.append(line + "\n")
        else:
            self._html_block_content.append(line)

        # Check end conditions based on type
        html_type = self._html_block_type
        line_lower = line.lower()

        # Type 1: ends with closing tag
        if html_type == 1:
            for tag in _HTML_BLOCK_TYPE1_TAGS:
                if f"</{tag}>" in line_lower:
                    yield from self._emit_html_block()
                    return

        # Type 2: ends with -->
        elif html_type == 2:
            if "-->" in line:
                yield from self._emit_html_block()
                return

        # Type 3: ends with ?>
        elif html_type == 3:
            if "?>" in line:
                yield from self._emit_html_block()
                return

        # Type 4: ends with >
        elif html_type == 4:
            if ">" in line:
                yield from self._emit_html_block()
                return

        # Type 5: ends with ]]>
        elif html_type == 5:
            if "]]>" in line:
                yield from self._emit_html_block()
                return

        # Types 6 and 7: end with blank line
        elif html_type in (6, 7) and not line.strip():
            # Remove the blank line from content (it's just the delimiter)
            if self._html_block_content:
                self._html_block_content.pop()
            yield from self._emit_html_block()
            return

        # Check for EOF - emit what we have
        if self._pos >= self._source_len:
            yield from self._emit_html_block()

    def _try_classify_list_marker(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token] | None:
        """Try to classify content as list item marker.

        Args:
            content: Line content with leading whitespace stripped
            line_start: Position in source where line starts
            indent: Number of leading spaces (for nesting detection)

        Yields marker token and content token if valid, returns None otherwise.
        The marker value includes leading spaces to preserve indent info for parser.
        """
        if not content:
            return None

        # Unordered: -, *, + (uses O(1) frozenset lookup)
        if content[0] in UNORDERED_LIST_MARKERS:
            if len(content) > 1 and content[1] in " \t":
                return self._yield_list_marker_and_content(
                    content[0], content[2:], line_start, indent
                )
            return None

        # Ordered: 1. or 1)
        if content[0].isdigit():
            pos = 0
            while pos < len(content) and content[pos].isdigit():
                pos += 1

            if pos > 9:
                # Too many digits
                return None

            if pos < len(content) and content[pos] in ".)":
                marker_char = content[pos]
                if pos + 1 < len(content) and content[pos + 1] in " \t":
                    num = content[:pos]
                    marker = f"{num}{marker_char}"
                    remaining = content[pos + 2 :]  # Skip marker and space
                    return self._yield_list_marker_and_content(
                        marker, remaining, line_start, indent
                    )

        return None

    def _yield_list_marker_and_content(
        self, marker: str, remaining: str, line_start: int, indent: int = 0
    ) -> Iterator[Token]:
        """Yield list marker token and optional content token.

        The marker value is prefixed with spaces to preserve indent for parser.
        E.g., indent=2, marker="-" yields value "  -" so parser knows nesting.

        Content after the marker is checked for block-level elements:
        - Thematic breaks (* * *, - - -, etc.)
        - Fenced code blocks
        """
        # Prefix marker with spaces to encode indent level
        indented_marker = " " * indent + marker
        yield Token(
            TokenType.LIST_ITEM_MARKER,
            indented_marker,
            self._location_from(line_start),
        )
        remaining = remaining.rstrip("\n")
        if not remaining:
            return

        # Check if content is a thematic break (e.g., "- * * *")
        if remaining.lstrip() and remaining.lstrip()[0] in THEMATIC_BREAK_CHARS:
            thematic_token = self._try_classify_thematic_break(remaining.lstrip(), line_start)
            if thematic_token:
                yield thematic_token
                return

        # Check if content starts a fenced code block
        if remaining.lstrip() and remaining.lstrip()[0] in FENCE_CHARS:
            fence_token = self._try_classify_fence_start(remaining.lstrip(), line_start, 0)
            if fence_token:
                yield fence_token
                return

        yield Token(
            TokenType.PARAGRAPH_LINE,
            remaining,
            self._location_from(line_start),
        )

    def _try_classify_link_reference_def(self, content: str, line_start: int) -> Token | None:
        """Try to classify content as link reference definition.

        Format: [label]: url "title"

        Returns LINK_REFERENCE_DEF token if valid, None otherwise.
        Token value format: label|url|title (pipe-separated)
        """
        if not content.startswith("["):
            return None

        # Find ]:
        bracket_end = content.find("]:")
        if bracket_end == -1 or bracket_end < 1:
            return None

        label = content[1:bracket_end]
        if not label:
            return None

        # Rest is URL and optional title
        rest = content[bracket_end + 2 :].strip()
        if not rest:
            return None

        # Parse URL (can be <url> or bare url)
        url = ""
        title = ""

        if rest.startswith("<"):
            # Angle-bracketed URL
            close_bracket = rest.find(">")
            if close_bracket != -1:
                url = rest[1:close_bracket]
                rest = rest[close_bracket + 1 :].strip()
        else:
            # Bare URL - ends at whitespace
            parts = rest.split(None, 1)
            url = parts[0] if parts else rest
            rest = parts[1] if len(parts) > 1 else ""

        # Parse optional title (in quotes or parentheses)
        if rest and (
            (rest.startswith('"') and rest.endswith('"'))
            or (rest.startswith("'") and rest.endswith("'"))
            or (rest.startswith("(") and rest.endswith(")"))
        ):
            title = rest[1:-1]

        if not url:
            return None

        # Value format: label|url|title
        value = f"{label}|{url}|{title}"
        return Token(TokenType.LINK_REFERENCE_DEF, value, self._location_from(line_start))

    def _try_classify_footnote_def(self, content: str, line_start: int) -> Token | None:
        """Try to classify content as footnote definition.

        Format: [^identifier]: content

        Returns FOOTNOTE_DEF token if valid, None otherwise.
        """
        if not content.startswith("[^"):
            return None

        # Find ]: after identifier
        bracket_end = content.find("]:")
        if bracket_end == -1 or bracket_end < 3:
            return None

        identifier = content[2:bracket_end]
        if not identifier:
            return None

        # Identifier must be alphanumeric with dashes/underscores
        if not all(c.isalnum() or c in "-_" for c in identifier):
            return None

        # Content after ]: (may be empty, with content on following lines)
        fn_content = content[bracket_end + 2 :].strip().rstrip("\n")

        # Value format: identifier:content
        value = f"{identifier}:{fn_content}"
        return Token(TokenType.FOOTNOTE_DEF, value, self._location_from(line_start))

    def _try_classify_directive_start(
        self, content: str, line_start: int
    ) -> Iterator[Token] | None:
        """Try to classify content as directive start.

        Detects :::{name} or ::::{name} syntax (MyST-style fenced directives).
        Supports:
        - Nested directives via colon count (:::: > :::)
        - Named closers (:::{/name})
        - Optional title after name

        Returns iterator of tokens if valid directive, None otherwise.
        """
        if not content.startswith(":::"):
            return None

        # Count opening colons
        colon_count = 0
        pos = 0
        while pos < len(content) and content[pos] == ":":
            colon_count += 1
            pos += 1

        if colon_count < 3:
            return None

        # Must have { immediately after colons
        if pos >= len(content) or content[pos] != "{":
            return None

        # Find matching }
        pos += 1  # Skip {
        brace_end = content.find("}", pos)
        if brace_end == -1:
            return None

        name = content[pos:brace_end].strip()

        # Check for named closer: {/name}
        is_closer = name.startswith("/")
        if is_closer:
            name = name[1:].strip()

        # Get optional title (rest of line after })
        title = content[brace_end + 1 :].rstrip("\n").strip()

        # Generate tokens
        return self._emit_directive_tokens(
            colon_count=colon_count,
            name=name,
            title=title,
            is_closer=is_closer,
            line_start=line_start,
        )

    def _emit_directive_tokens(
        self,
        colon_count: int,
        name: str,
        title: str,
        is_closer: bool,
        line_start: int,
    ) -> Iterator[Token]:
        """Emit directive tokens and update state."""
        location = self._location_from(line_start)

        if is_closer:
            # Named closer: :::{/name}
            yield Token(TokenType.DIRECTIVE_CLOSE, f":::{{{name}}}", location)

            # Pop from directive stack if matching
            if self._directive_stack:
                stack_count, stack_name = self._directive_stack[-1]
                if stack_name == name and colon_count >= stack_count:
                    self._directive_stack.pop()
                    if not self._directive_stack:
                        self._mode = LexerMode.BLOCK
        else:
            # Directive open
            yield Token(TokenType.DIRECTIVE_OPEN, ":" * colon_count, location)
            yield Token(TokenType.DIRECTIVE_NAME, name, location)
            if title:
                yield Token(TokenType.DIRECTIVE_TITLE, title, location)

            # Push to directive stack and switch mode
            self._directive_stack.append((colon_count, name))
            self._mode = LexerMode.DIRECTIVE

    def _scan_directive_content(self) -> Iterator[Token]:
        """Scan content inside a directive block.

        Handles:
        - Directive options (:key: value)
        - Nested directives (higher colon count)
        - Closing fence (matching or higher colon count)
        - All block-level elements (lists, headings, code, quotes, etc.)
        - Regular content (paragraph lines)
        """
        # Save location BEFORE scanning
        self._save_location()

        line_start = self._pos
        line_end = self._find_line_end()
        line = self._source[line_start:line_end]

        # Calculate indent and content
        indent, content_start = self._calc_indent(line)
        content = line[content_start:]

        # Commit position
        self._commit_to(line_end)

        # Empty line
        if not content or content.isspace():
            yield Token(TokenType.BLANK_LINE, "", self._location_from(line_start))
            return

        # Check for directive close (matching colon count or higher)
        if content.startswith(":::"):
            close_result = self._try_classify_directive_close(content, line_start)
            if close_result is not None:
                yield from close_result
                return

            # Could be nested directive start
            nested_result = self._try_classify_directive_start(content, line_start)
            if nested_result is not None:
                yield from nested_result
                return

        # Check for directive option (:key: value)
        # Only at the start of directive content, before any blank line
        if content.startswith(":") and not content.startswith(":::"):
            option_token = self._try_classify_directive_option(content, line_start)
            if option_token:
                yield option_token
                return

        # Fenced code: ``` or ~~~ (uses O(1) frozenset lookup)
        if content[0] in FENCE_CHARS:
            token = self._try_classify_fence_start(content, line_start)
            if token:
                yield token
                return

        # ATX Heading: # ## ### etc.
        if content.startswith("#"):
            token = self._try_classify_atx_heading(content, line_start)
            if token:
                yield token
                return

        # Thematic break: ---, ***, ___ (uses O(1) frozenset lookup)
        if content[0] in THEMATIC_BREAK_CHARS:
            token = self._try_classify_thematic_break(content, line_start)
            if token:
                yield token
                return

        # Block quote: >
        if content.startswith(">"):
            yield from self._classify_block_quote(content, line_start)
            return

        # List item: -, *, +, or 1. 1)
        # Pass indent so nested lists can be detected
        list_tokens = self._try_classify_list_marker(content, line_start, indent)
        if list_tokens is not None:
            yield from list_tokens
            return

        # Regular paragraph content
        yield Token(
            TokenType.PARAGRAPH_LINE,
            content.rstrip("\n"),
            self._location_from(line_start),
        )

    def _try_classify_directive_close(
        self, content: str, line_start: int
    ) -> Iterator[Token] | None:
        """Check if content is a directive closing fence.

        Valid closing:
        - ::: (simple close, 3+ colons matching or exceeding opener)
        - :::{/name} (named close)
        """
        if not content.startswith(":::"):
            return None

        # Count colons
        colon_count = 0
        pos = 0
        while pos < len(content) and content[pos] == ":":
            colon_count += 1
            pos += 1

        if colon_count < 3:
            return None

        # Check for named closer
        rest = content[pos:].strip().rstrip("\n")

        if rest.startswith("{/"):
            # Named closer: :::{/name}
            brace_end = rest.find("}")
            if brace_end != -1:
                name = rest[2:brace_end].strip()
                remaining = rest[brace_end + 1 :].strip()
                if not remaining:  # No extra content after }
                    return self._emit_directive_close(colon_count, name, line_start)

        elif rest == "" or rest.startswith("{"):
            # Simple close or check if it's a new directive
            if rest == "":
                # Simple close with just colons
                return self._emit_directive_close(colon_count, None, line_start)

        return None

    def _emit_directive_close(
        self, colon_count: int, name: str | None, line_start: int
    ) -> Iterator[Token]:
        """Emit directive close token and update state."""
        location = self._location_from(line_start)

        if not self._directive_stack:
            # No open directive, emit as plain text
            yield Token(TokenType.PARAGRAPH_LINE, ":" * colon_count, location)
            return

        stack_count, stack_name = self._directive_stack[-1]

        # Check if this closes the current directive or an outer one
        if name is not None:
            # Named closer: find matching directive in stack
            match_index = -1
            for i in range(len(self._directive_stack) - 1, -1, -1):
                s_count, s_name = self._directive_stack[i]
                if s_name == name and colon_count >= s_count:
                    match_index = i
                    break

            if match_index != -1:
                # Close this and all nested directives
                # Emit a separate DIRECTIVE_CLOSE token for each popped level
                # so the recursive parser can correctly exit all nested loops.
                popped_count = 0
                while len(self._directive_stack) > match_index:
                    s_count, s_name = self._directive_stack.pop()
                    popped_count += 1
                    # Use the original name for the first token, simple colons for others
                    # OR just use simple colons for all to be consistent.
                    # The parser only cares about the token type to break the loop.
                    if popped_count == 1:
                        yield Token(TokenType.DIRECTIVE_CLOSE, f":::{{{name}}}", location)
                    else:
                        yield Token(TokenType.DIRECTIVE_CLOSE, ":" * s_count, location)

                if not self._directive_stack:
                    self._mode = LexerMode.BLOCK
                return
        else:
            # Simple close: closes the top directive
            if colon_count >= stack_count:
                self._directive_stack.pop()
                yield Token(TokenType.DIRECTIVE_CLOSE, ":" * colon_count, location)

                if not self._directive_stack:
                    self._mode = LexerMode.BLOCK
                return

        # Not a valid close for current directive, emit as content
        yield Token(TokenType.PARAGRAPH_LINE, ":" * colon_count, location)

    def _try_classify_directive_option(self, content: str, line_start: int) -> Token | None:
        """Try to classify content as directive option.

        Format: :key: value
        """
        if not content.startswith(":"):
            return None

        # Find second colon
        colon_pos = content.find(":", 1)
        if colon_pos == -1:
            return None

        key = content[1:colon_pos].strip()
        value = content[colon_pos + 1 :].rstrip("\n").strip()

        # Key must be a valid identifier (alphanumeric + - + _)
        if not key or not all(c.isalnum() or c in "-_" for c in key):
            return None

        return Token(
            TokenType.DIRECTIVE_OPTION,
            f"{key}:{value}",
            self._location_from(line_start),
        )

    def _is_closing_fence(self, line: str) -> bool:
        """Check if line is a closing fence for current code block.

        CommonMark 4.5: Closing fences may be indented 0-3 spaces.
        If indented 4+ spaces, it's NOT a closing fence (it's code content).
        """
        if not self._fence_char:
            return False

        # Count leading spaces (CommonMark allows 0-3 spaces of indentation)
        indent = 0
        pos = 0
        while pos < len(line) and line[pos] == " ":
            indent += 1
            pos += 1

        # 4+ spaces of indent means NOT a closing fence
        if indent >= 4:
            return False

        content = line[pos:]

        if not content.startswith(self._fence_char):
            return False

        # Count fence characters
        count = 0
        fence_pos = 0
        while fence_pos < len(content) and content[fence_pos] == self._fence_char:
            count += 1
            fence_pos += 1

        if count < self._fence_count:
            return False

        # Rest must be whitespace only
        rest = content[fence_pos:].rstrip("\n")
        return rest.strip() == ""

    # =========================================================================
    # Window navigation helpers
    # =========================================================================

    def _find_line_end(self) -> int:
        """Find the end of the current line (position of \\n or EOF).

        Uses str.find for O(n) with low constant factor (C implementation).
        """
        idx = self._source.find("\n", self._pos)
        return idx if idx != -1 else self._source_len

    def _calc_indent(self, line: str) -> tuple[int, int]:
        """Calculate indent level and content start position.

        Returns:
            (indent_spaces, content_start_index)
        """
        indent = 0
        pos = 0
        line_len = len(line)  # Cache length
        while pos < line_len:
            char = line[pos]
            if char == " ":
                indent += 1
                pos += 1
            elif char == "\t":
                indent += 4 - (indent % 4)
                pos += 1
            else:
                break
        return indent, pos

    def _commit_to(self, line_end: int) -> None:
        """Commit position to line_end, consuming newline if present.

        Sets self._consumed_newline to indicate if a newline was consumed.
        Uses optimized string operations instead of character-by-character loop.
        """
        # Fast path: if no position change, skip
        if line_end == self._pos:
            self._consumed_newline = False
            if self._pos < self._source_len and self._source[self._pos] == "\n":
                self._pos += 1
                self._lineno += 1
                self._col = 1
                self._consumed_newline = True
            return

        # Count newlines in skipped segment using C-optimized str.count
        segment = self._source[self._pos : line_end]
        newline_count = segment.count("\n")

        if newline_count > 0:
            # Find position of last newline to calculate column
            last_nl = segment.rfind("\n")
            self._lineno += newline_count
            self._col = len(segment) - last_nl  # chars after last newline + 1
        else:
            self._col += len(segment)

        self._pos = line_end
        self._consumed_newline = False

        # Consume the newline if present
        if self._pos < self._source_len and self._source[self._pos] == "\n":
            self._pos += 1
            self._lineno += 1
            self._col = 1
            self._consumed_newline = True

    # =========================================================================
    # Character navigation helpers (kept for compatibility)
    # =========================================================================

    def _peek(self) -> str:
        """Peek at current character without advancing.

        Returns empty string at end of input.
        """
        if self._pos >= len(self._source):
            return ""
        return self._source[self._pos]

    def _advance(self) -> str:
        """Advance position by one character.

        Updates line/column tracking. Returns the consumed character.
        """
        if self._pos >= len(self._source):
            return ""

        char = self._source[self._pos]
        self._pos += 1

        if char == "\n":
            self._lineno += 1
            self._col = 1
        else:
            self._col += 1

        return char

    def _save_location(self) -> None:
        """Save current location for O(1) token location creation.

        Call this at the START of scanning a line, before any position changes.
        """
        self._saved_lineno = self._lineno
        self._saved_col = self._col

    def _location(self) -> SourceLocation:
        """Get current source location."""
        return SourceLocation(
            lineno=self._lineno,
            col_offset=self._col,
            offset=self._pos,
            end_offset=self._pos,
            source_file=self._source_file,
        )

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location from saved position.

        O(1) - uses pre-saved location from _save_location() call.
        """
        return SourceLocation(
            lineno=self._saved_lineno,
            col_offset=self._saved_col,
            offset=start_pos,
            end_offset=self._pos,
            end_lineno=self._lineno,
            end_col_offset=self._col,
            source_file=self._source_file,
        )
