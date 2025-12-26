"""Variable block parsing for Kida parser.

Provides mixin for parsing variable assignment statements (set, let, export).
"""

from __future__ import annotations

from bengal.rendering.kida._types import TokenType
from bengal.rendering.kida.nodes import Export, Let, Set
from bengal.rendering.kida.parser.blocks.core import BlockStackMixin


class VariableBlockParsingMixin(BlockStackMixin):
    """Mixin for parsing variable assignment blocks.

    Required Host Attributes:
        - All from BlockStackMixin
        - All from TokenNavigationMixin
        - _parse_expression: method
        - _parse_tuple_or_name: method
        - _parse_tuple_or_expression: method
        - _advance: method
        - _expect: method
        - _error: method
    """

    def _parse_set(self) -> Set:
        """Parse {% set x = expr %} or {% set a, b = 1, 2 %}."""
        start = self._advance()  # consume 'set'

        # Parse target - can be single name or tuple for unpacking
        target = self._parse_tuple_or_name()

        self._expect(TokenType.ASSIGN)

        # Parse value - may be an implicit tuple (e.g., 1, 2)
        value = self._parse_tuple_or_expression()
        self._expect(TokenType.BLOCK_END)

        return Set(
            lineno=start.lineno,
            col_offset=start.col_offset,
            target=target,
            value=value,
        )

    def _parse_let(self) -> Let:
        """Parse {% let x = expr %}."""
        start = self._advance()  # consume 'let'

        if self._current.type != TokenType.NAME:
            raise self._error("Expected variable name")
        name = self._advance().value

        self._expect(TokenType.ASSIGN)
        value = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        return Let(
            lineno=start.lineno,
            col_offset=start.col_offset,
            name=name,
            value=value,
        )

    def _parse_export(self) -> Export:
        """Parse {% export x = expr %}."""
        start = self._advance()  # consume 'export'

        if self._current.type != TokenType.NAME:
            raise self._error("Expected variable name")
        name = self._advance().value

        self._expect(TokenType.ASSIGN)
        value = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        return Export(
            lineno=start.lineno,
            col_offset=start.col_offset,
            name=name,
            value=value,
        )
