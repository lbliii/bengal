"""Block quote classifier mixin."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class QuoteClassifierMixin:
    """Mixin providing block quote classification."""

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location from saved position. Implemented by Lexer."""
        raise NotImplementedError

    def _expand_tabs(self, text: str, start_col: int = 1) -> str:
        """Expand tabs. Implemented by Lexer."""
        raise NotImplementedError

    def _classify_block_quote(self, content: str, line_start: int) -> Iterator[Token]:
        """Classify block quote marker and emit tokens.

        Block quotes start with > followed by optional space.
        If a tab follows >, it expands, and one space is consumed.

        Args:
            content: Line content starting with >
            line_start: Position in source where line starts

        Yields:
            BLOCK_QUOTE_MARKER token, then optional PARAGRAPH_LINE token.
        """
        # Yield the > marker
        yield Token(TokenType.BLOCK_QUOTE_MARKER, ">", self._location_from(line_start))

        # Content after >
        if len(content) > 1:
            # CommonMark 5.1: If the > is followed by a tab, it is treated as
            # if it were followed by the number of spaces needed to reach
            # the next tab stop. One space is consumed by the marker.

            # Expand the full content first (including potential tabs after >)
            # content[0] is '>', so content[1:] starts at column 2.
            # We assume initial indent is 0 for simplicity, or handle it via self._col
            # Lexer's _scan_block passes 'content' which has initial spaces stripped.
            # So > is at some column. Let's use a safe default or improve Lexer.
            expanded_rest = self._expand_tabs(content[1:], start_col=2)

            # Consume one space if present
            if expanded_rest and expanded_rest[0] == " ":
                remaining = expanded_rest[1:]
            else:
                remaining = expanded_rest

            if remaining:
                yield Token(
                    TokenType.PARAGRAPH_LINE,
                    remaining,
                    self._location_from(line_start),
                )
