"""Token navigation utilities for Kida parser.

Provides mixin for token stream navigation and basic parsing operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.kida._types import Token, TokenType

if TYPE_CHECKING:
    from bengal.rendering.kida.parser.errors import ParseError


class TokenNavigationMixin:
    """Mixin providing token stream navigation methods.

    Required Host Attributes:
        - _tokens: Sequence[Token]
        - _pos: int
        - _source: str | None
        - _filename: str | None
    """

    @property
    def _current(self) -> Token:
        """Get current token."""
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return Token(TokenType.EOF, "", 0, 0)

    def _peek(self, offset: int = 0) -> Token:
        """Peek at token at offset from current position."""
        pos = self._pos + offset
        if pos < len(self._tokens):
            return self._tokens[pos]
        return Token(TokenType.EOF, "", 0, 0)

    def _advance(self) -> Token:
        """Advance to next token and return current."""
        token = self._current
        self._pos += 1
        return token

    def _expect(self, token_type: TokenType) -> Token:
        """Expect current token to be of given type."""
        if self._current.type != token_type:
            # Provide helpful suggestions for common mistakes
            suggestion = None
            if token_type == TokenType.BLOCK_END:
                suggestion = "Add '%}' to close the block tag"
            elif token_type == TokenType.VARIABLE_END:
                suggestion = "Add '}}' to close the variable tag"
            raise self._error(
                f"Expected {token_type.value}, got {self._current.type.value}",
                suggestion=suggestion,
            )
        return self._advance()

    def _match(self, *types: TokenType) -> bool:
        """Check if current token matches any of the types."""
        return self._current.type in types

    def _error(
        self,
        message: str,
        token: Token | None = None,
        suggestion: str | None = None,
    ) -> ParseError:
        """Create a ParseError with source context and block stack info."""
        from bengal.rendering.kida.parser.errors import ParseError

        # Include block stack in error message if there are open blocks
        full_message = message
        if hasattr(self, "_block_stack") and self._block_stack:
            full_message = f"{message}\n\n{self._format_open_blocks()}"

        return ParseError(
            message=full_message,
            token=token or self._current,
            source=self._source,
            filename=self._filename,
            suggestion=suggestion,
        )
