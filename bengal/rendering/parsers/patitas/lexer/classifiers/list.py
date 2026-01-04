"""List marker classifier mixin."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.parsing.charsets import (
    FENCE_CHARS,
    THEMATIC_BREAK_CHARS,
    UNORDERED_LIST_MARKERS,
)
from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class ListClassifierMixin:
    """Mixin providing list marker classification."""

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location from saved position. Implemented by Lexer."""
        raise NotImplementedError

    def _try_classify_thematic_break(self, content: str, line_start: int) -> Token | None:
        """Try to classify content as thematic break. Implemented by ThematicClassifierMixin."""
        raise NotImplementedError

    def _try_classify_fence_start(
        self, content: str, line_start: int, indent: int = 0
    ) -> Token | None:
        """Try to classify content as fence start. Implemented by FenceClassifierMixin."""
        raise NotImplementedError

    def _try_classify_list_marker(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token] | None:
        """Try to classify content as list item marker.

        Handles both unordered (-, *, +) and ordered (1., 1)) list markers.

        Args:
            content: Line content with leading whitespace stripped
            line_start: Position in source where line starts
            indent: Number of leading spaces (for nesting detection)

        Returns:
            Iterator yielding marker and content tokens, or None if not a list.
        """
        if not content:
            return None

        # Unordered: -, *, + (uses O(1) frozenset lookup)
        if content[0] in UNORDERED_LIST_MARKERS:
            # Empty list item: just the marker at end of line
            if len(content) == 1:
                return self._yield_list_marker_and_content(content[0], "", line_start, indent)
            # Marker followed by space/tab, then optional content
            if content[1] == " ":
                return self._yield_list_marker_and_content(
                    content[0], content[2:], line_start, indent
                )
            if content[1] == "\t":
                # Tab after marker. Calculate expansion (marker at column indent + 1)
                # Tab at column indent + 2.
                col = indent + 2
                expansion = 4 - ((col - 1) % 4)
                # One space consumed by marker
                return self._yield_list_marker_and_content(
                    content[0], " " * (expansion - 1) + content[2:], line_start, indent
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
                num = content[:pos]
                marker = f"{num}{marker_char}"
                # Empty list item: just the marker at end of line (e.g., "1.\n")
                if pos + 1 == len(content):
                    return self._yield_list_marker_and_content(marker, "", line_start, indent)
                # Marker followed by space/tab, then optional content
                if content[pos + 1] == " ":
                    remaining = content[pos + 2 :]  # Skip marker and space
                    return self._yield_list_marker_and_content(
                        marker, remaining, line_start, indent
                    )
                if content[pos + 1] == "\t":
                    # Tab after marker. Calculate expansion.
                    # Marker length is pos + 1. It starts at col indent + 1.
                    # Tab starts at col indent + 1 + pos + 1 = indent + pos + 2.
                    col = indent + pos + 2
                    expansion = 4 - ((col - 1) % 4)
                    # One space consumed by marker
                    remaining = " " * (expansion - 1) + content[pos + 2 :]
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

        Args:
            marker: The list marker (e.g., "-", "1.")
            remaining: Content after the marker and space
            line_start: Position in source where line starts
            indent: Number of leading spaces

        Yields:
            LIST_ITEM_MARKER token, then optional content token.
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
