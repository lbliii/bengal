"""Fenced code mode scanner mixin."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.lexer.modes import LexerMode
from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class FenceScannerMixin:
    """Mixin providing fenced code mode scanning logic.

    Scans content inside fenced code blocks, detecting the closing fence.
    """

    # These will be set by the Lexer class
    _source: str
    _pos: int
    _mode: LexerMode
    _fence_char: str
    _fence_count: int
    _fence_info: str
    _fence_indent: int
    _consumed_newline: bool
    _directive_stack: list[tuple[int, str]]

    def _save_location(self) -> None:
        """Save current location for O(1) token location creation."""
        raise NotImplementedError

    def _find_line_end(self) -> int:
        """Find end of current line."""
        raise NotImplementedError

    def _commit_to(self, line_end: int) -> None:
        """Commit position to line_end."""
        raise NotImplementedError

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location from saved position."""
        raise NotImplementedError

    def _is_closing_fence(self, line: str) -> bool:
        """Check if line is a closing fence. Implemented by FenceClassifierMixin."""
        raise NotImplementedError

    def _scan_code_fence_content(self) -> Iterator[Token]:
        """Scan content inside fenced code block using window approach.

        Yields:
            FENCED_CODE_CONTENT tokens for each line, or FENCED_CODE_END
            when the closing fence is found.
        """
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
                line_indent=0,  # Closing fence indent is handled separately
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
            line_indent=0,  # Content indent is preserved in value
        )
