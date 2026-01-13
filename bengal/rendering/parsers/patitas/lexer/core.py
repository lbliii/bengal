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

from bengal.rendering.parsers.patitas.lexer.classifiers import (
    DirectiveClassifierMixin,
    FenceClassifierMixin,
    FootnoteClassifierMixin,
    HeadingClassifierMixin,
    HtmlClassifierMixin,
    LinkRefClassifierMixin,
    ListClassifierMixin,
    QuoteClassifierMixin,
    ThematicClassifierMixin,
)
from bengal.rendering.parsers.patitas.lexer.modes import LexerMode
from bengal.rendering.parsers.patitas.lexer.scanners import (
    BlockScannerMixin,
    DirectiveScannerMixin,
    FenceScannerMixin,
    HtmlScannerMixin,
)
from bengal.rendering.parsers.patitas.location import SourceLocation
from bengal.rendering.parsers.patitas.tokens import Token, TokenType


class Lexer(
    # Classifiers (pure logic, no position mutation)
    HeadingClassifierMixin,
    FenceClassifierMixin,
    ThematicClassifierMixin,
    QuoteClassifierMixin,
    ListClassifierMixin,
    LinkRefClassifierMixin,
    FootnoteClassifierMixin,
    HtmlClassifierMixin,
    DirectiveClassifierMixin,
    # Scanners (mode-specific scanning logic)
    BlockScannerMixin,
    FenceScannerMixin,
    DirectiveScannerMixin,
    HtmlScannerMixin,
):
    """State-machine lexer with O(n) guaranteed performance.
    
    Uses a window-based approach for block scanning:
    1. Scan to end of line (find window)
    2. Classify the line (pure logic, no position changes)
    3. Commit position (always advances)
    
    This eliminates rewinds and guarantees forward progress.
    
    Usage:
            >>> lexer = Lexer("# Hello\n\nWorld")
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
        "_html_block_indent",  # Indent of opening line for line_indent
        "_previous_line_blank",  # Track blank lines for inline HTML block decisions
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

        # Fenced code state
        self._fence_char: str = ""
        self._fence_count: int = 0
        self._fence_info: str = ""
        self._fence_indent: int = 0

        # HTML block state
        self._html_block_type: int = 0
        self._html_block_content: list[str] = []
        self._html_block_start: int = 0
        self._html_block_indent: int = 0
        self._previous_line_blank: bool = True

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

        yield Token(TokenType.EOF, "", self._location(), line_indent=0)

    def _dispatch_mode(self) -> Iterator[Token]:
        """Dispatch to appropriate scanner based on current mode.

        Yields:
            Token objects from the mode-specific scanner.
        """
        if self._mode == LexerMode.BLOCK:
            yield from self._scan_block()
        elif self._mode == LexerMode.CODE_FENCE:
            yield from self._scan_code_fence_content()
        elif self._mode == LexerMode.DIRECTIVE:
            yield from self._scan_directive_content()
        elif self._mode == LexerMode.HTML_BLOCK:
            yield from self._scan_html_block_content()

    # =========================================================================
    # Window navigation helpers
    # =========================================================================

    def _find_line_end(self) -> int:
        """Find the end of the current line (position of \\n or EOF).

        Uses str.find for O(n) with low constant factor (C implementation).

        Returns:
            Position of newline or end of source.
        """
        idx = self._source.find("\n", self._pos)
        return idx if idx != -1 else self._source_len

    def _calc_indent(self, line: str) -> tuple[int, int]:
        """Calculate indent level and content start position.

        Spaces count as 1, tabs expand to next multiple of 4.

        Args:
            line: Line content

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

    def _expand_tabs(self, text: str, start_col: int = 1) -> str:
        """Expand tabs in text to spaces based on start_col (1-indexed)."""
        result = []
        col = start_col
        for char in text:
            if char == "\t":
                expansion = 4 - ((col - 1) % 4)
                result.append(" " * expansion)
                col += expansion
            else:
                result.append(char)
                col += 1
        return "".join(result)

    def _commit_to(self, line_end: int) -> None:
        """Commit position to line_end, consuming newline if present.

        Sets self._consumed_newline to indicate if a newline was consumed.
        Uses optimized string operations instead of character-by-character loop.

        Args:
            line_end: Position to commit to.
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

        Returns:
            Current character or empty string at end of input.
        """
        if self._pos >= len(self._source):
            return ""
        return self._source[self._pos]

    def _advance(self) -> str:
        """Advance position by one character.

        Updates line/column tracking.

        Returns:
            The consumed character.
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

    # =========================================================================
    # Location tracking
    # =========================================================================

    def _save_location(self) -> None:
        """Save current location for O(1) token location creation.

        Call this at the START of scanning a line, before any position changes.
        """
        self._saved_lineno = self._lineno
        self._saved_col = self._col

    def _location(self) -> SourceLocation:
        """Get current source location.

        Returns:
            SourceLocation at current position.
        """
        return SourceLocation(
            lineno=self._lineno,
            col_offset=self._col,
            offset=self._pos,
            end_offset=self._pos,
            source_file=self._source_file,
        )

    def _location_from(
        self,
        start_pos: int,
        start_col: int | None = None,
        end_pos: int | None = None,
    ) -> SourceLocation:
        """Get source location from saved position.

        O(1) - uses pre-saved location from _save_location() call.

        Args:
            start_pos: Start position in source.
            start_col: Optional column override (1-indexed).
            end_pos: Optional end position override.

        Returns:
            SourceLocation spanning from start_pos to current or end_pos.
        """
        return SourceLocation(
            lineno=self._saved_lineno,
            col_offset=start_col if start_col is not None else self._saved_col,
            offset=start_pos,
            end_offset=end_pos if end_pos is not None else self._pos,
            end_lineno=self._lineno,
            end_col_offset=self._col,
            source_file=self._source_file,
        )
