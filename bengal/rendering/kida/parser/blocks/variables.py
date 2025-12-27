"""Variable block parsing for Kida parser.

Provides mixin for parsing variable assignment statements (set, let, export).
"""

from __future__ import annotations

from bengal.rendering.kida._types import TokenType
from bengal.rendering.kida.nodes import Export, Let, Set, Tuple
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
        - _peek: method
    """

    def _parse_set(self) -> list[Set]:
        """Parse {% set x = expr %} or {% set x = 1, y = 2, z = 3 %}.

        Multi-set syntax allows comma-separated independent assignments:
            {% set a = 1, b = 2, c = 3 %}

        Tuple unpacking remains unchanged:
            {% set a, b = 1, 2 %}

        IMPORTANT: For multi-set, uses _parse_expression() (not _parse_tuple_or_expression())
        to prevent commas from being consumed as tuple elements.

        Returns:
            List of Set nodes (one per assignment in multi-set, or single for regular set).
        """
        start = self._advance()  # consume 'set'
        sets: list[Set] = []

        while True:
            # Parse target - can be single name or tuple for unpacking
            target = self._parse_tuple_or_name()

            # Check for tuple unpacking (target is a tuple with multiple items)
            is_tuple_unpack = isinstance(target, Tuple) and len(target.items) > 1

            self._expect(TokenType.ASSIGN)

            if is_tuple_unpack:
                # Tuple unpacking: use _parse_tuple_or_expression for RHS
                # This handles {% set a, b = 1, 2 %}
                value = self._parse_tuple_or_expression()
                sets.append(
                    Set(
                        lineno=start.lineno,
                        col_offset=start.col_offset,
                        target=target,
                        value=value,
                    )
                )
                # Tuple unpacking cannot be combined with multi-set
                break
            else:
                # Single target: use _parse_expression to preserve commas
                value = self._parse_expression()

                # Check for multi-set continuation or tuple value: , ...
                if self._current.type == TokenType.COMMA:
                    if self._is_multi_set_continuation():
                        # Multi-set: a = 1, b = 2, c = 3
                        sets.append(
                            Set(
                                lineno=start.lineno,
                                col_offset=start.col_offset,
                                target=target,
                                value=value,
                            )
                        )
                        self._advance()  # consume comma
                        continue
                    else:
                        # Could be tuple value or trailing comma
                        # Parse rest as tuple: a = 1, 2, 3 -> tuple value
                        items = [value]
                        while self._current.type == TokenType.COMMA:
                            self._advance()  # consume comma
                            if self._match(TokenType.BLOCK_END):
                                break  # trailing comma
                            items.append(self._parse_expression())

                        if len(items) > 1:
                            # Create tuple value
                            value = Tuple(
                                lineno=items[0].lineno,
                                col_offset=items[0].col_offset,
                                items=tuple(items),
                                ctx="load",
                            )

                sets.append(
                    Set(
                        lineno=start.lineno,
                        col_offset=start.col_offset,
                        target=target,
                        value=value,
                    )
                )
                break

        self._expect(TokenType.BLOCK_END)
        return sets

    def _is_multi_set_continuation(self) -> bool:
        """Check if comma is followed by 'NAME =' pattern (multi-set).

        Uses 2-token lookahead without consuming tokens.

        Returns True for: a = 1, b = 2
        Returns False for: a = 1, 2, 3 (tuple value)
        Returns False for: a = 1, (trailing comma)
        """
        # Current token is COMMA
        # Peek ahead: NAME ASSIGN?
        next_token = self._peek(1)
        if next_token.type != TokenType.NAME:
            return False

        next_next_token = self._peek(2)
        return next_next_token.type == TokenType.ASSIGN

    def _parse_let(self) -> Let | list[Let]:
        """Parse {% let x = expr %} or {% let x = 1, y = 2, z = 3 %}.

        Multi-let syntax allows comma-separated independent assignments:
            {% let a = 1, b = 2, c = 3 %}

        Unlike set, let does not support tuple unpacking since let variables
        are always single names (template-scoped).

        Returns:
            Single Let node or list of Let nodes for multi-let.
        """
        start = self._advance()  # consume 'let'
        lets: list[Let] = []

        while True:
            if self._current.type != TokenType.NAME:
                raise self._error("Expected variable name")
            name = self._advance().value

            self._expect(TokenType.ASSIGN)
            value = self._parse_expression()

            lets.append(
                Let(
                    lineno=start.lineno,
                    col_offset=start.col_offset,
                    name=name,
                    value=value,
                )
            )

            # Check for multi-let continuation: , name =
            if self._current.type == TokenType.COMMA:
                if self._is_multi_set_continuation():
                    self._advance()  # consume comma
                    continue
                # Not multi-let, break (could be trailing comma)
            break

        self._expect(TokenType.BLOCK_END)

        # Return single node or list
        return lets[0] if len(lets) == 1 else lets

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
