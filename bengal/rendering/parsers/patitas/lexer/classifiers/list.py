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

    def _location_from(
        self, start_pos: int, start_col: int | None = None, end_pos: int | None = None
    ) -> SourceLocation:
        """Get source location from saved position. Implemented by Lexer."""
        raise NotImplementedError

    def _calc_indent(self, line: str) -> tuple[int, int]:
        """Calculate indent level. Implemented by Lexer."""
        raise NotImplementedError

    def _try_classify_list_marker(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token] | None:
        """Try to classify content as list item marker."""
        if not content:
            return None

        # Unordered: -, *, +
        if content[0] in UNORDERED_LIST_MARKERS:
            if len(content) == 1:
                return self._yield_list_marker_and_content(content[0], "", line_start, indent)
            if content[1] == " ":
                # CommonMark: one space after marker is consumed as part of marker structure
                return self._yield_list_marker_and_content(
                    content[0] + " ", content[2:], line_start, indent
                )
            if content[1] == "\t":
                col = indent + 2
                expansion = 4 - ((col - 1) % 4)
                return self._yield_list_marker_and_content(
                    content[0] + "\t", " " * (expansion - 1) + content[2:], line_start, indent
                )
            return None

        # Ordered: 1. or 1)
        if content[0].isdigit():
            pos = 0
            while pos < len(content) and content[pos].isdigit():
                pos += 1
            if pos > 9:
                return None
            if pos < len(content) and content[pos] in ".)":
                marker = content[: pos + 1]
                if pos + 1 == len(content):
                    return self._yield_list_marker_and_content(marker, "", line_start, indent)
                if content[pos + 1] == " ":
                    return self._yield_list_marker_and_content(
                        marker + " ", content[pos + 2 :], line_start, indent
                    )
                if content[pos + 1] == "\t":
                    col = indent + pos + 2
                    expansion = 4 - ((col - 1) % 4)
                    remaining = " " * (expansion - 1) + content[pos + 2 :]
                    return self._yield_list_marker_and_content(
                        marker + "\t", remaining, line_start, indent
                    )
        return None

    def _yield_list_marker_and_content(
        self, marker: str, remaining: str, line_start: int, indent: int = 0
    ) -> Iterator[Token]:
        """Yield list marker token and optional content tokens.

        Content after the marker is checked for block-level elements:
        - Thematic breaks (* * *, - - -, etc.)
        - Fenced code blocks
        - Block quotes
        - ATX headings
        - Nested list markers
        """
        marker_offset = line_start + indent

        indented_marker = " " * indent + marker
        yield Token(
            TokenType.LIST_ITEM_MARKER,
            indented_marker,
            self._location_from(
                marker_offset, start_col=indent + 1, end_pos=marker_offset + len(marker)
            ),
            line_indent=indent,
        )
        remaining = remaining.rstrip("\n")
        if not remaining:
            return

        stripped = remaining.lstrip()
        if not stripped:
            return

        # Calculate absolute column position after the marker
        leading_spaces = len(remaining) - len(stripped)
        content_col = indent + len(marker) + leading_spaces

        # Check for block-level elements in remaining content
        if stripped.startswith("#"):
            token = self._try_classify_atx_heading(stripped, line_start, content_col)
            if token:
                yield token
                return

        if stripped.startswith(">"):
            yield from self._classify_block_quote(stripped, line_start, content_col)
            return

        if stripped[0] in THEMATIC_BREAK_CHARS:
            token = self._try_classify_thematic_break(stripped, line_start, content_col)
            if token:
                yield token
                return

        if stripped[0] in FENCE_CHARS:
            token = self._try_classify_fence_start(stripped, line_start, content_col)
            if token:
                yield token
                return

        nested_tokens = self._try_classify_list_marker(stripped, line_start, content_col)
        if nested_tokens:
            yield from nested_tokens
            return

        # Default: paragraph line
        indented_content = " " * indent + remaining

        # Content offset for PARAGRAPH_LINE should start BEFORE leading spaces
        content_offset = line_start + indent + len(marker)

        # Calculate actual indentation of this line
        actual_indent, _ = self._calc_indent(indented_content)

        yield Token(
            TokenType.PARAGRAPH_LINE,
            indented_content,
            # Paragraph line spans to end of line
            self._location_from(content_offset, start_col=indent + len(marker) + 1),
            line_indent=actual_indent,
        )
