"""Control flow block parsing for Kida parser.

Provides mixin for parsing if/for control flow statements.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bengal.rendering.kida._types import TokenType
from bengal.rendering.kida.nodes import For, If

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Expr, Node

from bengal.rendering.kida.parser.blocks.core import BlockStackMixin


class ControlFlowBlockParsingMixin(BlockStackMixin):
    """Mixin for parsing control flow blocks.

    Required Host Attributes:
        - All from BlockStackMixin
        - All from TokenNavigationMixin
        - _parse_body: method
        - _parse_expression: method
        - _parse_for_target: method
        - _peek: method
        - _advance: method
        - _expect: method
        - _error: method
    """

    def _parse_if(self) -> If:
        """Parse {% if %} ... {% end %} or {% endif %}.

        Supports unified {% end %} as well as explicit {% endif %}.
        Also handles {% elif %} and {% else %} clauses.
        """
        start = self._advance()  # consume 'if'
        self._push_block("if", start)

        test = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        # Parse body, stopping on continuation (elif/else) or end keywords
        body = self._parse_body(stop_on_continuation=True)

        elif_: list[tuple[Expr, Sequence[Node]]] = []
        else_: list[Node] = []

        # Now we're at {% elif/else/end/endif
        while self._current.type == TokenType.BLOCK_BEGIN:
            next_tok = self._peek(1)
            if next_tok.type != TokenType.NAME:
                break

            keyword = next_tok.value

            if keyword == "elif":
                self._advance()  # consume {%
                self._advance()  # consume 'elif'
                elif_test = self._parse_expression()
                self._expect(TokenType.BLOCK_END)
                elif_body = self._parse_body(stop_on_continuation=True)
                elif_.append((elif_test, tuple(elif_body)))
            elif keyword == "else":
                self._advance()  # consume {%
                self._advance()  # consume 'else'
                self._expect(TokenType.BLOCK_END)
                # After else, only stop on end keywords (no more elif)
                else_ = self._parse_body(stop_on_continuation=False)
            elif keyword in ("end", "endif"):
                # Consume the end tag and pop from stack
                self._consume_end_tag("if")
                break
            else:
                # Unknown keyword - let parent handle it
                break

        return If(
            lineno=start.lineno,
            col_offset=start.col_offset,
            test=test,
            body=tuple(body),
            elif_=tuple(elif_),
            else_=tuple(else_),
        )

    def _parse_for(self) -> For:
        """Parse {% for %} ... {% end %} or {% endfor %.

        Supports unified {% end %} as well as explicit {% endfor %}.
        Also handles {% else %} and {% empty %} clauses.
        """
        start = self._advance()  # consume 'for'
        self._push_block("for", start)

        # Parse target (loop variable or tuple for unpacking)
        # Can be: item, (a, b), or a, b, c
        target = self._parse_for_target()

        # Expect 'in'
        if self._current.type != TokenType.IN:
            raise self._error(
                "Expected 'in' in for loop",
                suggestion="For loops use: {% for item in items %} or {% for a, b in items %}",
            )
        self._advance()

        # Parse iterable
        iter_expr = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        # Parse body - stop at continuation (else/empty) or end keywords
        body = self._parse_body(stop_on_continuation=True)

        empty: list[Node] = []

        # Now at {% else, {% empty, {% end, or {% endfor
        while self._current.type == TokenType.BLOCK_BEGIN:
            next_tok = self._peek(1)
            if next_tok.type != TokenType.NAME:
                break

            keyword = next_tok.value

            if keyword in ("else", "empty"):
                self._advance()  # consume {%
                self._advance()  # consume 'else' or 'empty'
                self._expect(TokenType.BLOCK_END)
                # After else/empty, only stop on end keywords
                empty = self._parse_body(stop_on_continuation=False)
            elif keyword in ("end", "endfor"):
                # Consume the end tag and pop from stack
                self._consume_end_tag("for")
                break
            else:
                # Unknown keyword - let parent handle it
                break

        return For(
            lineno=start.lineno,
            col_offset=start.col_offset,
            target=target,
            iter=iter_expr,
            body=tuple(body),
            empty=tuple(empty),
        )
