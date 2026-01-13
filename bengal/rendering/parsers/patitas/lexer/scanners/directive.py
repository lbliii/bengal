"""Directive mode scanner mixin."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.parsing.charsets import (
    FENCE_CHARS,
    THEMATIC_BREAK_CHARS,
)
from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class DirectiveScannerMixin:
    """Mixin providing directive mode scanning logic.
    
    Scans content inside directive blocks, handling:
    - Directive options (:key: value)
    - Nested directives (higher colon count)
    - Closing fence (matching or higher colon count)
    - All block-level elements (lists, headings, code, quotes, etc.)
    - Regular content (paragraph lines)
        
    """

    # These will be set by the Lexer class
    _source: str
    _pos: int

    def _save_location(self) -> None:
        """Save current location for O(1) token location creation."""
        raise NotImplementedError

    def _find_line_end(self) -> int:
        """Find end of current line."""
        raise NotImplementedError

    def _calc_indent(self, line: str) -> tuple[int, int]:
        """Calculate indent level and content start position."""
        raise NotImplementedError

    def _commit_to(self, line_end: int) -> None:
        """Commit position to line_end."""
        raise NotImplementedError

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location from saved position."""
        raise NotImplementedError

    # Classifier methods (provided by classifier mixins)
    def _try_classify_directive_close(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token] | None:
        raise NotImplementedError

    def _try_classify_directive_start(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token] | None:
        raise NotImplementedError

    def _try_classify_directive_option(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        raise NotImplementedError

    def _try_classify_fence_start(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        raise NotImplementedError

    def _try_classify_atx_heading(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        raise NotImplementedError

    def _try_classify_thematic_break(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        raise NotImplementedError

    def _classify_block_quote(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token]:
        raise NotImplementedError

    def _try_classify_list_marker(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token] | None:
        raise NotImplementedError

    def _scan_directive_content(self) -> Iterator[Token]:
        """Scan content inside a directive block.

        Handles:
        - Directive options (:key: value)
        - Nested directives (higher colon count)
        - Closing fence (matching or higher colon count)
        - All block-level elements (lists, headings, code, quotes, etc.)
        - Regular content (paragraph lines)

        Yields:
            Token objects for the current line.
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
            yield Token(TokenType.BLANK_LINE, "", self._location_from(line_start), line_indent=0)
            return

        # Check for directive close (matching colon count or higher)
        if content.startswith(":::"):
            close_result = self._try_classify_directive_close(content, line_start, indent)
            if close_result is not None:
                yield from close_result
                return

            # Could be nested directive start
            nested_result = self._try_classify_directive_start(content, line_start, indent)
            if nested_result is not None:
                yield from nested_result
                return

        # Check for directive option (:key: value)
        # Only at the start of directive content, before any blank line
        if content.startswith(":") and not content.startswith(":::"):
            option_token = self._try_classify_directive_option(content, line_start, indent)
            if option_token:
                yield option_token
                return

        # Fenced code: ``` or ~~~ (uses O(1) frozenset lookup)
        if content[0] in FENCE_CHARS:
            token = self._try_classify_fence_start(content, line_start, indent)
            if token:
                yield token
                return

        # ATX Heading: # ## ### etc.
        if content.startswith("#"):
            token = self._try_classify_atx_heading(content, line_start, indent)
            if token:
                yield token
                return

        # Thematic break: ---, ***, ___ (uses O(1) frozenset lookup)
        if content[0] in THEMATIC_BREAK_CHARS:
            token = self._try_classify_thematic_break(content, line_start, indent)
            if token:
                yield token
                return

        # Block quote: >
        if content.startswith(">"):
            yield from self._classify_block_quote(content, line_start, indent)
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
            line_indent=indent,
        )
