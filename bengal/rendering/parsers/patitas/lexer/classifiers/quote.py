"""Block quote classifier mixin."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class QuoteClassifierMixin:
    """Mixin providing block quote classification."""

    def _location_from(
        self, start_pos: int, start_col: int | None = None, end_pos: int | None = None
    ) -> SourceLocation:
        """Get source location from saved position. Implemented by Lexer."""
        raise NotImplementedError

    def _expand_tabs(self, text: str, start_col: int = 1) -> str:
        """Expand tabs. Implemented by Lexer."""
        raise NotImplementedError

    def _classify_block_quote(
        self, content: str, line_start: int, indent: int = 0
    ) -> Iterator[Token]:
        """Classify block quote marker and emit tokens.

        Args:
            content: Content starting with >
            line_start: Absolute offset of the start of the line
            indent: Column position of the > marker (0-indexed)
        """
        # The > marker is at line_start + indent (for 0-3 spaces)
        marker_offset = line_start + indent

        # Yield the > marker
        yield Token(
            TokenType.BLOCK_QUOTE_MARKER,
            ">",
            self._location_from(marker_offset, start_col=indent + 1, end_pos=marker_offset + 1),
            line_indent=indent,
        )

        # Content after >
        if len(content) > 1:
            expanded_rest = self._expand_tabs(content[1:], start_col=indent + 2)

            # Consume one space if present
            if expanded_rest and expanded_rest[0] == " ":
                remaining = expanded_rest[1:]
                sub_indent = indent + 2
            else:
                remaining = expanded_rest
                sub_indent = indent + 1

            if remaining:
                stripped = remaining.lstrip()
                if not stripped:
                    return

                # Calculate absolute column position
                leading_spaces = len(remaining) - len(stripped)
                content_col = sub_indent + leading_spaces

                # Check for block-level elements in remaining content
                if stripped.startswith("#"):
                    token = self._try_classify_atx_heading(stripped, line_start, content_col)
                    if token:
                        yield token
                        return
                # Link reference definitions inside block quotes should be recognized
                if stripped.startswith("[") and not stripped.startswith("[^"):
                    link_ref_token = self._try_classify_link_reference_def(
                        stripped, line_start, content_col
                    )
                    if link_ref_token:
                        yield link_ref_token
                        return

                if stripped.startswith(">"):
                    yield from self._classify_block_quote(stripped, line_start, content_col)
                    return

                from bengal.rendering.parsers.patitas.parsing.charsets import (
                    FENCE_CHARS,
                    THEMATIC_BREAK_CHARS,
                )

                if stripped[0] in THEMATIC_BREAK_CHARS:
                    token = self._try_classify_thematic_break(stripped, line_start, content_col)
                    if token:
                        yield token
                        return

                if stripped[0] in FENCE_CHARS:
                    # Don't change lexer mode - blockquote parser handles fence content
                    token = self._try_classify_fence_start(
                        stripped, line_start, content_col, change_mode=False
                    )
                    if token:
                        yield token
                        return

                nested_tokens = self._try_classify_list_marker(stripped, line_start, content_col)
                if nested_tokens:
                    yield from nested_tokens
                    return

                # Link reference definitions inside block quotes are still global.
                if stripped.startswith("[") and not stripped.startswith("[^"):
                    link_ref = self._try_classify_link_reference_def(
                        stripped, line_start, indent=leading_spaces
                    )
                    if link_ref is not None:
                        yield link_ref
                        return

                # Default: paragraph line
                # Use remaining content directly - don't add synthetic indentation.
                # The actual indentation is tracked via line_indent.
                content_offset = line_start + sub_indent

                yield Token(
                    TokenType.PARAGRAPH_LINE,
                    remaining,
                    self._location_from(content_offset, start_col=sub_indent + 1),
                    line_indent=leading_spaces,  # Track actual leading spaces in content
                )
