"""Token navigation utilities for Patitas parser.

Provides mixin for token stream navigation and basic parsing operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.parsers.patitas.tokens import Token, TokenType

if TYPE_CHECKING:
    from collections.abc import Sequence


class TokenNavigationMixin:
    """Mixin providing token stream navigation methods.

    Required Host Attributes:
        - _tokens: Sequence[Token]
        - _pos: int
        - _current: Token | None
    """

    _tokens: Sequence[Token]
    _pos: int
    _current: Token | None

    def _at_end(self) -> bool:
        """Check if at end of token stream."""
        return self._current is None or self._current.type == TokenType.EOF

    def _advance(self) -> Token | None:
        """Advance to next token and return it."""
        self._pos += 1
        if self._pos < len(self._tokens):
            self._current = self._tokens[self._pos]
        else:
            self._current = None
        return self._current

    def _peek(self, offset: int = 1) -> Token | None:
        """Peek at token at offset from current position."""
        pos = self._pos + offset
        if pos < len(self._tokens):
            return self._tokens[pos]
        return None
