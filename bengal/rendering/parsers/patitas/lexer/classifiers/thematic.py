"""Thematic break classifier mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class ThematicClassifierMixin:
    """Mixin providing thematic break classification."""

    def _location_from(
        self, start_pos: int, start_col: int | None = None, end_pos: int | None = None
    ) -> SourceLocation:
        """Get source location from saved position. Implemented by Lexer."""
        raise NotImplementedError

    def _try_classify_thematic_break(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        """Try to classify content as thematic break.

        Thematic breaks are 3+ of the same character (-, *, _) with
        optional spaces/tabs between them.

        Args:
            content: Line content with leading whitespace stripped
            line_start: Position in source where line starts
            indent: Number of leading spaces (for line_indent)

        Returns:
            Token if valid break, None otherwise.
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
            # Preserve original content so parser can distinguish setext underlines
            # A pure sequence like "---" can become setext h2, but "--- -" cannot
            return Token(
                TokenType.THEMATIC_BREAK,
                content.rstrip("\n"),
                self._location_from(line_start),
                line_indent=indent,
            )

        return None
