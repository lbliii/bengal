"""ATX heading classifier mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class HeadingClassifierMixin:
    """Mixin providing ATX heading classification."""

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location from saved position. Implemented by Lexer."""
        raise NotImplementedError

    def _try_classify_atx_heading(self, content: str, line_start: int) -> Token | None:
        """Try to classify content as ATX heading.

        ATX headings start with 1-6 # characters followed by space/tab/newline/end.
        Trailing # sequences are removed if preceded by space.

        Args:
            content: Line content with leading whitespace stripped
            line_start: Position in source where line starts

        Returns:
            Token if valid heading, None otherwise.
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
