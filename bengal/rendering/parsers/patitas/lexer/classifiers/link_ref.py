"""Link reference definition classifier mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation


class LinkRefClassifierMixin:
    """Mixin providing link reference definition classification."""

    def _location_from(self, start_pos: int) -> SourceLocation:
        """Get source location from saved position. Implemented by Lexer."""
        raise NotImplementedError

    def _try_classify_link_reference_def(self, content: str, line_start: int) -> Token | None:
        """Try to classify content as link reference definition.

        Format: [label]: url "title"

        Args:
            content: Line content with leading whitespace stripped
            line_start: Position in source where line starts

        Returns:
            LINK_REFERENCE_DEF token if valid, None otherwise.
            Token value format: label|url|title (pipe-separated)
        """
        if not content.startswith("["):
            return None

        # Find ]:
        bracket_end = content.find("]:")
        if bracket_end == -1 or bracket_end < 1:
            return None

        label = content[1:bracket_end]
        if not label:
            return None

        # Rest is URL and optional title
        rest = content[bracket_end + 2 :].strip()
        if not rest:
            return None

        # Parse URL (can be <url> or bare url)
        url = ""
        title = ""

        url_is_empty_angle = False
        if rest.startswith("<"):
            # Angle-bracketed URL - can be empty <>
            close_bracket = rest.find(">")
            if close_bracket != -1:
                url = rest[1:close_bracket]
                url_is_empty_angle = close_bracket == 1  # <> means empty URL
                rest = rest[close_bracket + 1 :].strip()
            else:
                return None  # Unclosed angle bracket
        else:
            # Bare URL - ends at whitespace
            parts = rest.split(None, 1)
            url = parts[0] if parts else rest
            rest = parts[1] if len(parts) > 1 else ""

        # Parse optional title (in quotes or parentheses)
        if rest and (
            (rest.startswith('"') and rest.endswith('"'))
            or (rest.startswith("'") and rest.endswith("'"))
            or (rest.startswith("(") and rest.endswith(")"))
        ):
            title = rest[1:-1]

        # Empty URL is only valid with angle brackets <>
        if not url and not url_is_empty_angle:
            return None

        # Value format: label|url|title
        value = f"{label}|{url}|{title}"
        return Token(TokenType.LINK_REFERENCE_DEF, value, self._location_from(line_start))
