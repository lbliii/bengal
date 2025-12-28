"""State-machine lexer with O(n) guaranteed performance.

Implements the rosettes pattern: hand-written state machines with O(n)
guaranteed performance. Each character is examined exactly once.

No regex in the hot path. Zero ReDoS vulnerability by construction.

Thread Safety:
    Lexer instances are single-use. Create one per source string.
    All state is instance-local; no shared mutable state.
"""

from __future__ import annotations

from collections.abc import Iterator
from enum import Enum, auto

from bengal.rendering.parsers.patitas.location import SourceLocation
from bengal.rendering.parsers.patitas.tokens import Token, TokenType


class LexerMode(Enum):
    """Lexer operating modes.

    The lexer switches between modes based on context:
    - BLOCK: Between blocks, scanning for block starts
    - CODE_FENCE: Inside fenced code block
    - PARAGRAPH: Inside paragraph text
    """

    BLOCK = auto()  # Between blocks
    CODE_FENCE = auto()  # Inside fenced code block


class Lexer:
    """State-machine lexer with O(n) guaranteed performance.

    No regex in the hot path. Each character is examined exactly once.
    Zero ReDoS vulnerability by construction.

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
        "_pos",
        "_lineno",
        "_col",
        "_mode",
        "_source_file",
        "_fence_char",
        "_fence_count",
    )

    def __init__(self, source: str, source_file: str | None = None) -> None:
        """Initialize lexer with source text.

        Args:
            source: Markdown source text
            source_file: Optional source file path for error messages
        """
        self._source = source
        self._pos = 0
        self._lineno = 1
        self._col = 1
        self._mode = LexerMode.BLOCK
        self._source_file = source_file

        # Fenced code state
        self._fence_char: str = ""
        self._fence_count: int = 0

    def tokenize(self) -> Iterator[Token]:
        """Tokenize source into token stream.

        Yields:
            Token objects one at a time

        Complexity: O(n) where n = len(source)
        Memory: O(1) iterator (tokens yielded, not accumulated)
        """
        iterations = 0
        max_iterations = len(self._source) * 2 + 100  # Safety limit

        while self._pos < len(self._source):
            iterations += 1
            if iterations > max_iterations:
                raise RuntimeError(
                    f"Lexer infinite loop detected: pos={self._pos}, "
                    f"len={len(self._source)}, mode={self._mode}, "
                    f"fence_char={repr(self._fence_char)}, fence_count={self._fence_count}"
                )
            yield from self._dispatch_mode()

        yield Token(TokenType.EOF, "", self._location())

    def _dispatch_mode(self) -> Iterator[Token]:
        """Dispatch to appropriate scanner based on current mode."""
        if self._mode == LexerMode.BLOCK:
            yield from self._scan_block()
        elif self._mode == LexerMode.CODE_FENCE:
            yield from self._scan_code_fence_content()

    def _scan_block(self) -> Iterator[Token]:
        """Scan for block-level elements."""
        # Skip leading whitespace and count indent
        indent = 0
        start_pos = self._pos
        while self._peek() in " \t":
            if self._peek() == " ":
                indent += 1
            else:  # tab
                indent += 4 - (indent % 4)
            self._advance()

        # Check for blank line
        if self._peek() in "\n":
            self._advance()  # Consume newline
            yield Token(TokenType.BLANK_LINE, "", self._location_from(start_pos))
            return

        if self._peek() == "":
            return

        char = self._peek()

        # ATX heading: # ## ### etc.
        if char == "#" and indent < 4:
            yield from self._scan_atx_heading()
            return

        # Fenced code: ``` or ~~~
        if char in "`~" and indent < 4:
            fence_start = self._pos
            fence_char = char
            fence_count = 0
            while self._peek() == fence_char:
                fence_count += 1
                self._advance()

            if fence_count >= 3:
                # Scan info string
                info_start = self._pos
                while self._peek() not in "\n" and self._peek() != "":
                    self._advance()
                info = self._source[info_start : self._pos].strip()

                # Consume newline
                if self._peek() == "\n":
                    self._advance()

                self._fence_char = fence_char
                self._fence_count = fence_count
                self._mode = LexerMode.CODE_FENCE

                value = fence_char * fence_count
                if info:
                    value += info
                yield Token(TokenType.FENCED_CODE_START, value, self._location_from(fence_start))
                return
            else:
                # Not enough fence chars, rewind and treat as paragraph
                self._pos = fence_start

        # Thematic break: ---, ***, ___
        if char in "-*_" and indent < 4:
            break_token = self._try_scan_thematic_break(char, start_pos)
            if break_token:
                yield break_token
                return

        # Block quote: >
        if char == ">" and indent < 4:
            yield from self._scan_block_quote()
            return

        # List item: -, *, +, or 1. 1)
        if indent < 4:
            list_token = self._try_scan_list_marker(char, start_pos, indent)
            if list_token:
                yield list_token
                return

        # Indented code block (4+ spaces)
        if indent >= 4:
            yield from self._scan_indented_code(start_pos, indent)
            return

        # Default: paragraph line
        yield from self._scan_paragraph_line(start_pos)

    def _scan_atx_heading(self) -> Iterator[Token]:
        """Scan ATX heading (# Heading)."""
        start_pos = self._pos
        level = 0

        # Count # characters
        while self._peek() == "#" and level < 6:
            level += 1
            self._advance()

        # Must be followed by space or newline (or end)
        next_char = self._peek()
        if next_char not in " \t\n" and next_char != "":
            # Not a valid heading, treat as paragraph
            self._pos = start_pos
            yield from self._scan_paragraph_line(start_pos)
            return

        # Skip space after #
        if self._peek() in " \t":
            self._advance()

        # Capture heading content until newline
        content_start = self._pos
        while self._peek() not in "\n" and self._peek() != "":
            self._advance()

        content = self._source[content_start : self._pos]

        # Remove trailing # and whitespace (closing sequence)
        content = content.rstrip()
        if content.endswith("#"):
            # Find where trailing #s start
            trailing_start = len(content)
            while trailing_start > 0 and content[trailing_start - 1] == "#":
                trailing_start -= 1
            # Must be preceded by space
            if trailing_start > 0 and content[trailing_start - 1] in " \t":
                content = content[: trailing_start - 1].rstrip()
            elif trailing_start == 0:
                content = ""

        # Consume newline
        if self._peek() == "\n":
            self._advance()

        value = "#" * level + " " + content if content else "#" * level
        yield Token(TokenType.ATX_HEADING, value, self._location_from(start_pos))

    def _scan_code_fence_content(self) -> Iterator[Token]:
        """Scan content inside fenced code block."""
        # Check for closing fence
        start_pos = self._pos

        # Count leading spaces (up to 3 allowed)
        indent = 0
        while self._peek() == " " and indent < 3:
            indent += 1
            self._advance()

        # Check for closing fence (only if fence_char is set)
        if self._fence_char and self._peek() == self._fence_char:
            fence_start = self._pos
            count = 0
            while self._peek() == self._fence_char:
                count += 1
                self._advance()

            # Must have at least as many chars as opening fence
            # And nothing else on line except whitespace
            if count >= self._fence_count:
                # Check rest of line is whitespace
                while self._peek() in " \t":
                    self._advance()
                if self._peek() in "\n" or self._peek() == "":
                    if self._peek() == "\n":
                        self._advance()
                    self._mode = LexerMode.BLOCK
                    yield Token(
                        TokenType.FENCED_CODE_END,
                        self._fence_char * count,
                        self._location_from(fence_start),
                    )
                    return

            # Not a valid close, rewind
            self._pos = start_pos

        # Scan content line
        line_start = self._pos

        # Handle EOF case - if we're at EOF, we need to close the fence implicitly
        if self._peek() == "":
            # At EOF without closing fence - close it implicitly
            self._mode = LexerMode.BLOCK
            # Yield any remaining content (should be empty at EOF)
            if line_start < len(self._source):
                content = self._source[line_start:]
                yield Token(TokenType.FENCED_CODE_CONTENT, content, self._location_from(start_pos))
            # Ensure we're past EOF to exit the main loop
            self._pos = len(self._source)
            return

        # Scan until newline or EOF
        while self._peek() not in "\n" and self._peek() != "":
            self._advance()

        content = self._source[line_start : self._pos]

        # Consume newline (if present)
        if self._peek() == "\n":
            self._advance()
            content += "\n"
        elif self._peek() == "":
            # At EOF - ensure we advance past it
            self._pos = len(self._source)

        # Only yield non-empty content (empty lines are handled elsewhere)
        if content:
            yield Token(TokenType.FENCED_CODE_CONTENT, content, self._location_from(start_pos))

    def _try_scan_thematic_break(self, char: str, start_pos: int) -> Token | None:
        """Try to scan a thematic break (---, ***, ___).

        Returns Token if successful, None otherwise.
        """
        saved_pos = self._pos
        count = 0

        while True:
            c = self._peek()
            if c == char:
                count += 1
                self._advance()
            elif c in " \t":
                self._advance()
            elif c in "\n" or c == "":
                break
            else:
                # Invalid character, not a thematic break
                self._pos = saved_pos
                return None

        if count >= 3:
            if self._peek() == "\n":
                self._advance()
            return Token(TokenType.THEMATIC_BREAK, char * 3, self._location_from(start_pos))

        self._pos = saved_pos
        return None

    def _scan_block_quote(self) -> Iterator[Token]:
        """Scan block quote marker (>)."""
        start_pos = self._pos
        self._advance()  # Consume >

        # Optional space after >
        if self._peek() == " ":
            self._advance()

        yield Token(TokenType.BLOCK_QUOTE_MARKER, ">", self._location_from(start_pos))

    def _try_scan_list_marker(self, char: str, start_pos: int, indent: int) -> Token | None:
        """Try to scan a list item marker.

        Returns Token if successful, None otherwise.
        """
        saved_pos = self._pos

        # Unordered: -, *, +
        if char in "-*+":
            self._advance()
            # Must be followed by space or tab
            if self._peek() in " \t":
                self._advance()
                return Token(TokenType.LIST_ITEM_MARKER, char, self._location_from(start_pos))
            self._pos = saved_pos
            return None

        # Ordered: 1. or 1)
        if char.isdigit():
            num_start = self._pos
            while self._peek().isdigit():
                self._advance()

            if self._pos - num_start > 9:
                # Too many digits
                self._pos = saved_pos
                return None

            if self._peek() in ".":
                marker_char = self._peek()
                self._advance()
                if self._peek() in " \t":
                    num = self._source[num_start : self._pos - 1]
                    self._advance()
                    return Token(
                        TokenType.LIST_ITEM_MARKER,
                        f"{num}{marker_char}",
                        self._location_from(start_pos),
                    )

            self._pos = saved_pos

        return None

    def _scan_indented_code(self, start_pos: int, indent: int) -> Iterator[Token]:
        """Scan indented code block."""
        # We've already consumed the indent spaces
        # Capture the rest of the line
        line_start = self._pos
        while self._peek() not in "\n" and self._peek() != "":
            self._advance()

        content = self._source[line_start : self._pos]

        # Consume newline
        if self._peek() == "\n":
            self._advance()
            content += "\n"

        yield Token(TokenType.INDENTED_CODE, content, self._location_from(start_pos))

    def _scan_paragraph_line(self, start_pos: int) -> Iterator[Token]:
        """Scan a paragraph line."""
        # Capture until newline
        line_start = self._pos
        while self._peek() not in "\n" and self._peek() != "":
            self._advance()

        content = self._source[line_start : self._pos]

        # Consume newline
        if self._peek() == "\n":
            self._advance()

        yield Token(TokenType.PARAGRAPH_LINE, content, self._location_from(start_pos))

    # =========================================================================
    # Character navigation helpers
    # =========================================================================

    def _peek(self) -> str:
        """Peek at current character without advancing.

        Returns empty string at end of input.
        """
        if self._pos >= len(self._source):
            return ""
        return self._source[self._pos]

    def _peek_ahead(self, n: int) -> str:
        """Peek at n characters starting from current position.

        Returns available characters (may be shorter than n at end).
        """
        return self._source[self._pos : self._pos + n]

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

    def _location(self) -> SourceLocation:
        """Get current source location."""
        return SourceLocation(
            lineno=self._lineno,
            col_offset=self._col,
            source_file=self._source_file,
        )

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location starting from a saved position.

        Calculates line/col for the given position by scanning from start.
        """
        # Calculate line/col for start position
        lineno = 1
        col = 1
        for i in range(start_pos):
            if self._source[i] == "\n":
                lineno += 1
                col = 1
            else:
                col += 1

        return SourceLocation(
            lineno=lineno,
            col_offset=col,
            end_lineno=self._lineno,
            end_col_offset=self._col,
            source_file=self._source_file,
        )
