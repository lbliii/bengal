"""Function block parsing for Kida parser.

Provides mixin for parsing function and macro related statements (macro, def, call, slot).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.kida._types import TokenType
from bengal.rendering.kida.nodes import CallBlock, Def, Macro, Slot

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Expr

from bengal.rendering.kida.parser.blocks.core import BlockStackMixin


class FunctionBlockParsingMixin(BlockStackMixin):
    """Mixin for parsing function and macro blocks.

    Required Host Attributes:
        - All from BlockStackMixin
        - All from TokenNavigationMixin
        - _parse_body: method
        - _parse_expression: method
        - _parse_call_args: method
        - _match: method
        - _advance: method
        - _expect: method
        - _error: method
    """

    def _parse_macro(self) -> Macro:
        """Parse {% macro name(args) %}...{% end %} or {% endmacro %}."""
        start = self._advance()  # consume 'macro'
        self._push_block("macro", start)

        # Get macro name
        if self._current.type != TokenType.NAME:
            raise self._error("Expected macro name")
        name = self._advance().value

        # Parse arguments
        args: list[str] = []
        defaults: list[Expr] = []

        self._expect(TokenType.LPAREN)
        while not self._match(TokenType.RPAREN):
            if args:
                self._expect(TokenType.COMMA)
            if self._current.type != TokenType.NAME:
                raise self._error("Expected argument name")
            arg_name = self._advance().value
            args.append(arg_name)

            # Check for default value
            if self._match(TokenType.ASSIGN):
                self._advance()
                defaults.append(self._parse_expression())

        self._expect(TokenType.RPAREN)
        self._expect(TokenType.BLOCK_END)

        # Parse body using universal end detection
        body = self._parse_body()

        # Consume end tag
        self._consume_end_tag("macro")

        return Macro(
            lineno=start.lineno,
            col_offset=start.col_offset,
            name=name,
            args=tuple(args),
            body=tuple(body),
            defaults=tuple(defaults),
        )

    def _parse_def(self) -> Def:
        """Parse {% def name(args) %}...{% end %} or {% enddef %.

        Kida functions with true lexical scoping (can access outer scope).
        Uses stack-based parsing for proper nested block handling.

        Example:
            {% def card(item, show_date=true) %}
                <div>{{ item.title }}</div>
                {% if show_date %}{{ item.date }}{% end %}
                <span>From: {{ site.title }}</span>  {# outer scope access #}
            {% end %}

            {{ card(page) }}
        """
        start = self._advance()  # consume 'def'
        self._push_block("def", start)

        # Get function name
        if self._current.type != TokenType.NAME:
            raise self._error(
                "Expected function name",
                suggestion="Function syntax: {% def name(args) %}...{% end %}",
            )
        name = self._advance().value

        # Parse arguments
        args: list[str] = []
        defaults: list[Expr] = []

        self._expect(TokenType.LPAREN)
        while not self._match(TokenType.RPAREN):
            if args:
                self._expect(TokenType.COMMA)
            if self._current.type != TokenType.NAME:
                raise self._error("Expected argument name")
            arg_name = self._advance().value
            args.append(arg_name)

            # Check for default value
            if self._match(TokenType.ASSIGN):
                self._advance()
                defaults.append(self._parse_expression())

        self._expect(TokenType.RPAREN)
        self._expect(TokenType.BLOCK_END)

        # Parse body using universal end detection
        body = self._parse_body()

        # Consume end tag
        self._consume_end_tag("def")

        return Def(
            lineno=start.lineno,
            col_offset=start.col_offset,
            name=name,
            args=tuple(args),
            body=tuple(body),
            defaults=tuple(defaults),
        )

    def _parse_call(self) -> CallBlock:
        """Parse {% call name(args) %}body{% end %} or {% endcall %.

        Call a function/def with body content that fills {% slot %}.

        Example:
            {% call card("My Title") %}
                <p>This content goes in the slot!</p>
            {% end %}
        """
        start = self._advance()  # consume 'call'
        self._push_block("call", start)

        # Parse the call expression
        call_expr = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        # Parse body using universal end detection
        body = self._parse_body()

        # Consume end tag
        self._consume_end_tag("call")

        return CallBlock(
            lineno=start.lineno,
            col_offset=start.col_offset,
            call=call_expr,
            body=tuple(body),
        )

    def _parse_slot(self) -> Slot:
        """Parse {% slot %} or {% slot name %.

        Placeholder inside {% def %} where caller content goes.

        Example:
            {% def card(title) %}
                <div class="card">
                    <h3>{{ title }}</h3>
                    <div class="body">{% slot %}</div>
                </div>
            {% enddef %}
        """
        start = self._advance()  # consume 'slot'

        # Optional slot name (default is "default")
        name = "default"
        if self._current.type == TokenType.NAME:
            name = self._advance().value

        self._expect(TokenType.BLOCK_END)

        return Slot(
            lineno=start.lineno,
            col_offset=start.col_offset,
            name=name,
        )
