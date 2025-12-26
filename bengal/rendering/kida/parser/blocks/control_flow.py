"""Control flow block parsing for Kida parser.

Provides mixin for parsing if/for control flow statements.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bengal.rendering.kida._types import TokenType
from bengal.rendering.kida.nodes import Break, Continue, For, If, Match, UnaryOp

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

    def _parse_unless(self) -> If:
        """Parse {% unless cond %} as {% if not cond %}.

        Part of RFC: kida-modern-syntax-features.
        Supports {% end %}, {% endif %}, and {% endunless %}.
        """
        start = self._advance()  # consume 'unless'
        self._push_block("unless", start)  # Track as 'unless' for endunless support

        # Parse condition
        condition = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        # Parse body, stopping on continuation (else) or end keywords
        body = self._parse_body(stop_on_continuation=True)

        else_: list[Node] = []

        # Handle optional else clause
        while self._current.type == TokenType.BLOCK_BEGIN:
            next_tok = self._peek(1)
            if next_tok.type != TokenType.NAME:
                break

            keyword = next_tok.value

            if keyword == "else":
                self._advance()  # consume {%
                self._advance()  # consume 'else'
                self._expect(TokenType.BLOCK_END)
                else_ = self._parse_body(stop_on_continuation=False)
            elif keyword in ("end", "endif", "endunless"):
                self._consume_end_tag("unless")
                break
            else:
                break

        # Create If with negated condition: unless x == if not x
        return If(
            lineno=start.lineno,
            col_offset=start.col_offset,
            test=UnaryOp(
                lineno=condition.lineno,
                col_offset=condition.col_offset,
                op="not",
                operand=condition,
            ),
            body=tuple(body),
            elif_=(),
            else_=tuple(else_),
        )

    def _parse_break(self) -> Break:
        """Parse {% break %} loop control.

        Part of RFC: kida-modern-syntax-features.
        """
        start = self._advance()  # consume 'break'

        if not self._in_loop():
            raise self._error(
                "'break' outside loop",
                suggestion="Use 'break' only inside {% for %} or {% while %} loops",
            )

        self._expect(TokenType.BLOCK_END)
        return Break(lineno=start.lineno, col_offset=start.col_offset)

    def _parse_continue(self) -> Continue:
        """Parse {% continue %} loop control.

        Part of RFC: kida-modern-syntax-features.
        """
        start = self._advance()  # consume 'continue'

        if not self._in_loop():
            raise self._error(
                "'continue' outside loop",
                suggestion="Use 'continue' only inside {% for %} or {% while %} loops",
            )

        self._expect(TokenType.BLOCK_END)
        return Continue(lineno=start.lineno, col_offset=start.col_offset)

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
        Supports inline if filter: {% for x in items if x.visible %}
        Part of RFC: kida-modern-syntax-features (inline if).
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

        # Parse iterable - use _parse_null_coalesce_no_ternary() to support ??
        # but avoid parsing 'if' as ternary. This allows both:
        #   {% for x in items ?? [] %}           ← null coalescing
        #   {% for x in items if x.visible %}    ← inline filter
        # Part of RFC: kida-modern-syntax-features
        iter_expr = self._parse_null_coalesce_no_ternary()

        # Check for inline filter: {% for x in items if condition %}
        # Part of RFC: kida-modern-syntax-features
        test = None
        if self._current.type == TokenType.NAME and self._current.value == "if":
            self._advance()  # consume 'if'
            test = self._parse_or()  # Parse the condition (also without ternary)

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
            test=test,
        )

    def _parse_match(self) -> Match:
        """Parse {% match expr %}{% case pattern %}...{% end %}.

        Pattern matching for cleaner branching than if/elif chains.
        Reuses the existing _parse_body infrastructure for case bodies.

        Syntax:
            {% match page.type %}
                {% case "post" %}...
                {% case "gallery" %}...
                {% case _ %}...
            {% end %}

        The underscore (_) is the wildcard/default case.
        """
        start = self._advance()  # consume 'match'
        self._push_block("match", start)

        # Parse subject expression
        subject = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        cases: list[tuple[Expr, Sequence[Node]]] = []

        # Parse case clauses
        # Skip DATA tokens (whitespace between {% match %} and {% case %})
        while self._current.type != TokenType.EOF:
            # Skip DATA tokens (whitespace/text between blocks)
            if self._current.type == TokenType.DATA:
                self._advance()
                continue

            # Skip comments
            if self._current.type == TokenType.COMMENT_BEGIN:
                self._skip_comment()
                continue

            if self._current.type != TokenType.BLOCK_BEGIN:
                break

            next_tok = self._peek(1)
            if next_tok.type != TokenType.NAME:
                break

            keyword = next_tok.value

            if keyword == "case":
                self._advance()  # consume {%
                self._advance()  # consume 'case'

                # Parse pattern expression - use _parse_null_coalesce_no_ternary
                # to avoid consuming 'if' as a ternary conditional
                # This allows: {% case _ if guard %} without the 'if' being parsed
                # as part of a conditional expression
                pattern = self._parse_null_coalesce_no_ternary()

                # Check for optional guard clause: {% case pattern if guard %}
                guard: Expr | None = None
                if self._current.type == TokenType.NAME and self._current.value == "if":
                    self._advance()  # consume 'if'
                    guard = self._parse_expression()

                self._expect(TokenType.BLOCK_END)

                # Parse case body - reuse existing _parse_body
                # stop_on_continuation=True stops at next "case" or end keywords
                body = self._parse_body(stop_on_continuation=True)
                cases.append((pattern, guard, tuple(body)))

            elif keyword in ("end", "endmatch"):
                self._consume_end_tag("match")
                break
            else:
                # Unknown keyword - error
                raise self._error(
                    f"Expected 'case' or 'end' in match block, got '{keyword}'",
                    suggestion="Match blocks contain {% case pattern %} clauses",
                )

        if not cases:
            raise self._error(
                "Match block must have at least one {% case %} clause",
                suggestion="Add {% case value %}...{% end %} inside the match block",
            )

        return Match(
            lineno=start.lineno,
            col_offset=start.col_offset,
            subject=subject,
            cases=tuple(cases),
        )
