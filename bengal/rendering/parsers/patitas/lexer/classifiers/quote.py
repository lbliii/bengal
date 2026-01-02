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

    def _classify_block_quote(self, content: str, line_start: int) -> Iterator[Token]:
        """Classify block quote marker and emit tokens.

        Block quotes start with > followed by optional space.
        Remaining content is emitted as a paragraph line.

        Args:
            content: Line content starting with >
            line_start: Position in source where line starts

        Yields:
            BLOCK_QUOTE_MARKER token, then optional PARAGRAPH_LINE token.
        """
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
