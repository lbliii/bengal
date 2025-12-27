"""Expression parsing for Kida parser.

Provides mixin for parsing expressions (ternary, binary, unary, primary, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.kida._types import TokenType
from bengal.rendering.kida.nodes import (
    BinOp,
    BoolOp,
    Compare,
    CondExpr,
    Const,
    Dict,
    Filter,
    FuncCall,
    Getattr,
    Getitem,
    List,
    Name,
    NullCoalesce,
    OptionalGetattr,
    OptionalGetitem,
    Pipeline,
    Range,
    Slice,
    Test,
    Tuple,
    UnaryOp,
)

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Expr

# Python-style boolean/none keywords (canonical)
# Lowercase also accepted for convenience
BOOL_TRUE = frozenset({"True", "true"})
BOOL_FALSE = frozenset({"False", "false"})
BOOL_NONE = frozenset({"None", "none"})
BOOL_KEYWORDS = BOOL_TRUE | BOOL_FALSE | BOOL_NONE


class ExpressionParsingMixin:
    """Mixin for parsing expressions.

    Required Host Attributes:
        - All from TokenNavigationMixin
        - _parse_call_args: method
    """

    def _parse_expression(self) -> Expr:
        """Parse expression with ternary and null coalescing.

        Filters are handled at higher precedence (in _parse_unary_postfix).
        Null coalescing (??) has lowest precedence (below or).
        """
        return self._parse_null_coalesce()

    def _parse_null_coalesce(self) -> Expr:
        """Parse null coalescing: a ?? b.

        Returns b if a is None/undefined, otherwise a.
        Right-associative: a ?? b ?? c = a ?? (b ?? c)
        Part of RFC: kida-modern-syntax-features.
        """
        left = self._parse_ternary()

        while self._match(TokenType.NULLISH_COALESCE):
            self._advance()  # consume ??
            # Right-associative: parse right side as full null coalesce
            right = self._parse_null_coalesce()
            left = NullCoalesce(
                lineno=left.lineno,
                col_offset=left.col_offset,
                left=left,
                right=right,
            )

        return left

    def _parse_ternary(self) -> Expr:
        """Parse ternary conditional: a if b else c

        Jinja2 also supports short form: a if b (defaults to '' if false)

        The condition can include filters because filters have higher precedence
        than comparisons: x if y | length > 0 else z
        """
        # Parse the "true" value first
        expr = self._parse_or()

        # Check for "if" keyword
        if self._current.type == TokenType.NAME and self._current.value == "if":
            self._advance()  # consume "if"

            # Parse condition using full expression (filters handled in postfix)
            test = self._parse_or()

            # Check for optional "else" - Jinja2 allows short form: 's' if x (returns '' if false)
            if self._current.type == TokenType.NAME and self._current.value == "else":
                self._advance()  # consume "else"
                # Parse the "false" value (right-associative)
                else_expr = self._parse_ternary()
            else:
                # Short form: return empty string if condition is false
                else_expr = Const(
                    lineno=expr.lineno,
                    col_offset=expr.col_offset,
                    value="",
                )

            return CondExpr(
                lineno=expr.lineno,
                col_offset=expr.col_offset,
                test=test,
                if_true=expr,
                if_false=else_expr,
            )

        return expr

    def _parse_null_coalesce_no_ternary(self) -> Expr:
        """Parse null coalescing without ternary support.

        Used in for loops where we need ?? but not ternary (to preserve inline if):
            {% for x in items ?? [] %}           ← works
            {% for x in items if x.visible %}    ← still works

        Part of RFC: kida-modern-syntax-features.
        """
        left = self._parse_or()

        while self._match(TokenType.NULLISH_COALESCE):
            self._advance()  # consume ??
            # Right-associative: parse right side recursively
            right = self._parse_null_coalesce_no_ternary()
            left = NullCoalesce(
                lineno=left.lineno,
                col_offset=left.col_offset,
                left=left,
                right=right,
            )

        return left

    def _parse_or(self) -> Expr:
        """Parse 'or' expression."""
        return self._parse_binary(self._parse_and, TokenType.OR)

    def _parse_and(self) -> Expr:
        """Parse 'and' expression."""
        return self._parse_binary(self._parse_not, TokenType.AND)

    def _parse_not(self) -> Expr:
        """Parse 'not' expression."""
        if self._match(TokenType.NOT):
            token = self._advance()
            operand = self._parse_not()
            return UnaryOp(
                lineno=token.lineno,
                col_offset=token.col_offset,
                op="not",
                operand=operand,
            )
        return self._parse_comparison()

    def _parse_comparison(self) -> Expr:
        """Parse comparison expression."""
        left = self._parse_addition()

        ops = []
        comparators = []

        while self._match(
            TokenType.EQ,
            TokenType.NE,
            TokenType.LT,
            TokenType.LE,
            TokenType.GT,
            TokenType.GE,
            TokenType.IN,
            TokenType.IS,
            TokenType.NOT,  # For 'not in'
        ):
            op_token = self._advance()
            op = op_token.value

            # Handle 'not in': when we see 'not', expect 'in' to follow
            if op == "not":
                if self._match(TokenType.IN):
                    self._advance()
                    op = "not in"
                else:
                    raise self._error(
                        "Expected 'in' after 'not' in comparison",
                        suggestion="Use 'not in' for membership test: {% if item not in items %}",
                    )
            elif op == "is" and self._match(TokenType.NOT):
                self._advance()
                op = "is not"

            # Handle tests: "is defined", "is not mapping", "is sameas false", etc.
            if op in ("is", "is not"):
                # Check if next token is a test name (NAME token, but NOT a boolean keyword)
                # Boolean keywords like True/False/None should be identity comparisons, not tests
                if (
                    self._current.type == TokenType.NAME
                    and self._current.value not in BOOL_KEYWORDS
                ):
                    test_name = self._advance().value

                    # Parse optional arguments
                    # Jinja2 style: is divisibleby(3) OR is sameas false (no parens)
                    test_args: list[Expr] = []
                    test_kwargs: dict[str, Expr] = {}
                    if self._match(TokenType.LPAREN):
                        # Arguments in parentheses: is divisibleby(3)
                        self._advance()
                        test_args, test_kwargs = self._parse_call_args()
                        self._expect(TokenType.RPAREN)
                    elif self._can_start_test_arg():
                        # Single argument without parens: is sameas false, is sameas none
                        # Only parse simple values to avoid ambiguity
                        test_args = [self._parse_primary()]

                    # Create Test node
                    left = Test(
                        lineno=left.lineno,
                        col_offset=left.col_offset,
                        value=left,
                        name=test_name,
                        args=tuple(test_args),
                        kwargs=test_kwargs,
                        negated=(op == "is not"),
                    )
                    continue  # Don't add to ops/comparators
                else:
                    # Regular "is" comparison (identity check)
                    pass

            ops.append(op)
            comparators.append(self._parse_addition())

        if ops:
            return Compare(
                lineno=left.lineno,
                col_offset=left.col_offset,
                left=left,
                ops=tuple(ops),
                comparators=tuple(comparators),
            )

        return left

    def _can_start_test_arg(self) -> bool:
        """Check if current token can start a test argument without parens.

        Used for: is sameas False, is sameas None
        Only allow simple values to avoid ambiguity with following expressions.
        """
        # Allow: True, False, None, numbers, strings
        if self._current.type in (TokenType.INTEGER, TokenType.FLOAT, TokenType.STRING):
            return True
        if self._current.type == TokenType.NAME:
            # Only allow boolean/none keywords as bare args
            return self._current.value in BOOL_KEYWORDS
        return False

    def _parse_addition(self) -> Expr:
        """Parse addition/subtraction/concatenation.

        The ~ operator is string concatenation in Jinja.
        """
        return self._parse_binary(
            self._parse_multiplication_with_filters,
            TokenType.ADD,
            TokenType.SUB,
            TokenType.TILDE,
        )

    def _parse_multiplication_with_filters(self) -> Expr:
        """Parse multiplication/division with filter chain.

        Filters are applied after multiplication but before addition:
        a + b | filter  parses as  a + (b | filter)
        a * b | filter  parses as  (a * b) | filter
        -42 | abs       parses as  (-42) | abs  → 42
        """
        expr = self._parse_multiplication()
        return self._parse_filter_chain(expr)

    def _parse_multiplication(self) -> Expr:
        """Parse multiplication/division."""
        return self._parse_binary(
            self._parse_unary,
            TokenType.MUL,
            TokenType.DIV,
            TokenType.FLOORDIV,
            TokenType.MOD,
        )

    def _parse_unary(self) -> Expr:
        """Parse unary operators.

        Unary operators bind tighter than filters:
        -42|abs  parses as  (-42)|abs  → 42
        """
        if self._match(TokenType.SUB, TokenType.ADD):
            token = self._advance()
            operand = self._parse_unary()
            return UnaryOp(
                lineno=token.lineno,
                col_offset=token.col_offset,
                op="-" if token.type == TokenType.SUB else "+",
                operand=operand,
            )
        return self._parse_power()

    def _parse_power(self) -> Expr:
        """Parse power operator."""
        left = self._parse_primary_postfix()

        if self._match(TokenType.POW):
            self._advance()
            right = self._parse_unary()  # Right associative
            return BinOp(
                lineno=left.lineno,
                col_offset=left.col_offset,
                op="**",
                left=left,
                right=right,
            )

        return left

    def _parse_primary_postfix(self) -> Expr:
        """Parse primary expressions with postfix operators (., [], (), ?., ?[).

        Does NOT include filter operator (|) - filters are parsed at a
        lower precedence level in _parse_filter_chain.

        Supports optional chaining: ?. and ?[ (RFC: kida-modern-syntax-features).
        """
        expr = self._parse_primary()

        while True:
            if self._match(TokenType.DOT):
                self._advance()
                if self._current.type != TokenType.NAME:
                    raise self._error("Expected attribute name")
                attr = self._advance().value
                expr = Getattr(
                    lineno=expr.lineno,
                    col_offset=expr.col_offset,
                    obj=expr,
                    attr=attr,
                )
            elif self._match(TokenType.OPTIONAL_DOT):
                # Optional chaining: obj?.attr
                # Part of RFC: kida-modern-syntax-features
                self._advance()
                if self._current.type != TokenType.NAME:
                    raise self._error("Expected attribute name after ?.")
                attr = self._advance().value
                expr = OptionalGetattr(
                    lineno=expr.lineno,
                    col_offset=expr.col_offset,
                    obj=expr,
                    attr=attr,
                )
            elif self._match(TokenType.LBRACKET):
                self._advance()
                key = self._parse_subscript()
                self._expect(TokenType.RBRACKET)
                expr = Getitem(
                    lineno=expr.lineno,
                    col_offset=expr.col_offset,
                    obj=expr,
                    key=key,
                )
            elif self._match(TokenType.OPTIONAL_BRACKET):
                # Optional subscript: obj?[key]
                # Part of RFC: kida-modern-syntax-features
                self._advance()
                key = self._parse_subscript()
                self._expect(TokenType.RBRACKET)
                expr = OptionalGetitem(
                    lineno=expr.lineno,
                    col_offset=expr.col_offset,
                    obj=expr,
                    key=key,
                )
            elif self._match(TokenType.LPAREN):
                self._advance()
                args, kwargs = self._parse_call_args()
                self._expect(TokenType.RPAREN)
                expr = FuncCall(
                    lineno=expr.lineno,
                    col_offset=expr.col_offset,
                    func=expr,
                    args=tuple(args),
                    kwargs=kwargs,
                )
            elif self._match(TokenType.RANGE_INCLUSIVE, TokenType.RANGE_EXCLUSIVE):
                # Range literal: 1..10 or 1...11
                # Part of RFC: kida-modern-syntax-features
                expr = self._parse_range(expr)
            else:
                break

        return expr

    def _parse_range(self, start: Expr) -> Range:
        """Parse range literal after seeing start value.

        Syntax:
            1..10    → inclusive range [1, 10]
            1...11   → exclusive range [1, 11) (like Python range)
            1..10 by 2  → range with step

        Part of RFC: kida-modern-syntax-features.
        """
        inclusive = self._current.type == TokenType.RANGE_INCLUSIVE
        self._advance()  # consume .. or ...

        # Parse end value
        end = self._parse_unary()  # Use unary for precedence

        # Optional step: 'by' keyword
        step: Expr | None = None
        if self._current.type == TokenType.NAME and self._current.value == "by":
            self._advance()  # consume 'by'
            step = self._parse_unary()

        return Range(
            lineno=start.lineno,
            col_offset=start.col_offset,
            start=start,
            end=end,
            inclusive=inclusive,
            step=step,
        )

    def _parse_filter_chain(self, expr: Expr) -> Expr:
        """Parse filter chain: expr | filter1 | filter2(arg).

        Also handles pipeline operator: expr |> filter1 |> filter2(arg).

        Design: Mixing | and |> in the same expression is not allowed.
        The first operator encountered determines the style for the expression.

        Filters are parsed after unary operators:
        -42|abs  parses as  (-42)|abs  → 42
        """
        # Check for pipeline operator first
        if self._match(TokenType.PIPELINE):
            return self._parse_pipeline(expr)

        # Standard filter chain with |
        while self._match(TokenType.PIPE):
            self._advance()

            # Error if switching from | to |> mid-expression
            if self._match(TokenType.PIPELINE):
                raise self._error(
                    "Cannot mix '|' and '|>' operators in the same expression",
                    suggestion="Use either '|' or '|>' consistently: {{ x | a | b }} or {{ x |> a |> b }}",
                )

            if self._current.type != TokenType.NAME:
                raise self._error("Expected filter name")
            filter_name = self._advance().value

            args: list[Expr] = []
            kwargs: dict[str, Expr] = {}

            # Optional arguments
            if self._match(TokenType.LPAREN):
                self._advance()
                args, kwargs = self._parse_call_args()
                self._expect(TokenType.RPAREN)

            expr = Filter(
                lineno=expr.lineno,
                col_offset=expr.col_offset,
                value=expr,
                name=filter_name,
                args=tuple(args),
                kwargs=kwargs,
            )

        # Error if switching from | to |> after the filter chain
        if self._match(TokenType.PIPELINE):
            raise self._error(
                "Cannot mix '|' and '|>' operators in the same expression",
                suggestion="Use either '|' or '|>' consistently: {{ x | a | b }} or {{ x |> a |> b }}",
            )

        return expr

    def _parse_pipeline(self, expr: Expr) -> Expr:
        """Parse pipeline chain: expr |> filter1 |> filter2(arg).

        Pipelines are left-associative: a |> b |> c == (a |> b) |> c

        Each step is a filter application. The pipeline collects all
        steps into a single Pipeline node for potential optimization.

        Design: Mixing | and |> is not allowed. Error on | after |>.
        """
        from collections.abc import Sequence

        steps: list[tuple[str, Sequence[Expr], dict[str, Expr]]] = []

        while self._match(TokenType.PIPELINE):
            self._advance()  # consume |>

            if self._current.type != TokenType.NAME:
                raise self._error(
                    "Expected filter name after |>",
                    suggestion="Pipeline syntax: expr |> filter_name or expr |> filter_name(args)",
                )

            filter_name = self._advance().value

            args: list[Expr] = []
            kwargs: dict[str, Expr] = {}

            # Optional arguments
            if self._match(TokenType.LPAREN):
                self._advance()
                args, kwargs = self._parse_call_args()
                self._expect(TokenType.RPAREN)

            steps.append((filter_name, tuple(args), kwargs))

        # Error if switching from |> to | mid-expression
        if self._match(TokenType.PIPE):
            raise self._error(
                "Cannot mix '|>' and '|' operators in the same expression",
                suggestion="Use either '|>' or '|' consistently: {{ x |> a |> b }} or {{ x | a | b }}",
            )

        if not steps:
            return expr

        return Pipeline(
            lineno=expr.lineno,
            col_offset=expr.col_offset,
            value=expr,
            steps=tuple(steps),
        )

    def _parse_subscript(self) -> Expr:
        """Parse subscript: key or slice [start:stop:step]."""
        lineno = self._current.lineno
        col = self._current.col_offset

        # Check if this is a slice (starts with : or has : after first expr)
        start: Expr | None = None
        stop: Expr | None = None
        step: Expr | None = None

        # Parse start (if not starting with :)
        if not self._match(TokenType.COLON):
            start = self._parse_expression()

            # If no colon follows, this is just a regular subscript
            if not self._match(TokenType.COLON):
                return start

        # Consume first colon
        self._advance()

        # Parse stop (if not : or ])
        if not self._match(TokenType.COLON, TokenType.RBRACKET):
            stop = self._parse_expression()

        # Check for step
        if self._match(TokenType.COLON):
            self._advance()
            if not self._match(TokenType.RBRACKET):
                step = self._parse_expression()

        return Slice(
            lineno=lineno,
            col_offset=col,
            start=start,
            stop=stop,
            step=step,
        )

    def _parse_primary(self) -> Expr:
        """Parse primary expression."""
        token = self._current

        # String literal
        if token.type == TokenType.STRING:
            self._advance()
            return Const(
                lineno=token.lineno,
                col_offset=token.col_offset,
                value=token.value,
            )

        # Integer literal
        if token.type == TokenType.INTEGER:
            self._advance()
            return Const(
                lineno=token.lineno,
                col_offset=token.col_offset,
                value=int(token.value),
            )

        # Float literal
        if token.type == TokenType.FLOAT:
            self._advance()
            return Const(
                lineno=token.lineno,
                col_offset=token.col_offset,
                value=float(token.value),
            )

        # Name or keyword constant
        if token.type == TokenType.NAME:
            self._advance()
            if token.value in BOOL_TRUE:
                return Const(token.lineno, token.col_offset, True)
            elif token.value in BOOL_FALSE:
                return Const(token.lineno, token.col_offset, False)
            elif token.value in BOOL_NONE:
                return Const(token.lineno, token.col_offset, None)
            return Name(
                lineno=token.lineno,
                col_offset=token.col_offset,
                name=token.value,
            )

        # Parenthesized expression or tuple
        if token.type == TokenType.LPAREN:
            self._advance()
            if self._match(TokenType.RPAREN):
                self._advance()
                return Tuple(token.lineno, token.col_offset, ())

            expr = self._parse_expression()

            if self._match(TokenType.COMMA):
                # Tuple
                items = [expr]
                while self._match(TokenType.COMMA):
                    self._advance()
                    if self._match(TokenType.RPAREN):
                        break
                    items.append(self._parse_expression())
                self._expect(TokenType.RPAREN)
                return Tuple(token.lineno, token.col_offset, tuple(items))

            self._expect(TokenType.RPAREN)
            return expr

        # List
        if token.type == TokenType.LBRACKET:
            self._advance()
            items = []
            if not self._match(TokenType.RBRACKET):
                items.append(self._parse_expression())
                while self._match(TokenType.COMMA):
                    self._advance()
                    if self._match(TokenType.RBRACKET):
                        break
                    items.append(self._parse_expression())
            self._expect(TokenType.RBRACKET)
            return List(token.lineno, token.col_offset, tuple(items))

        # Dict literal: {} or {key: value, ...}
        if token.type == TokenType.LBRACE:
            self._advance()
            keys = []
            values = []
            if not self._match(TokenType.RBRACE):
                # Parse first key:value pair
                key = self._parse_expression()
                self._expect(TokenType.COLON)
                value = self._parse_expression()
                keys.append(key)
                values.append(value)
                # Parse remaining pairs
                while self._match(TokenType.COMMA):
                    self._advance()
                    if self._match(TokenType.RBRACE):
                        break
                    key = self._parse_expression()
                    self._expect(TokenType.COLON)
                    value = self._parse_expression()
                    keys.append(key)
                    values.append(value)
            self._expect(TokenType.RBRACE)
            return Dict(token.lineno, token.col_offset, tuple(keys), tuple(values))

        raise self._error(
            f"Unexpected token: {token.type.value}",
            token=token,
            suggestion="Expected a value (string, number, variable name, list, or dict)",
        )

    def _parse_binary(self, operand_parser, *op_types: TokenType) -> Expr:
        """Generic binary expression parser."""
        left = operand_parser()

        while self._match(*op_types):
            op_token = self._advance()
            right = operand_parser()

            if op_token.type in (TokenType.AND, TokenType.OR):
                left = BoolOp(
                    lineno=left.lineno,
                    col_offset=left.col_offset,
                    op="and" if op_token.type == TokenType.AND else "or",
                    values=(left, right),
                )
            else:
                left = BinOp(
                    lineno=left.lineno,
                    col_offset=left.col_offset,
                    op=self._token_to_op(op_token.type),
                    left=left,
                    right=right,
                )

        return left

    def _parse_call_args(self) -> tuple[list[Expr], dict[str, Expr]]:
        """Parse function call arguments."""
        args: list[Expr] = []
        kwargs: dict[str, Expr] = {}

        if self._match(TokenType.RPAREN):
            return args, kwargs

        while True:
            # Check for keyword argument
            if self._current.type == TokenType.NAME and self._peek(1).type == TokenType.ASSIGN:
                name = self._advance().value
                self._advance()  # consume =
                kwargs[name] = self._parse_expression()
            else:
                args.append(self._parse_expression())

            if not self._match(TokenType.COMMA):
                break
            self._advance()

        return args, kwargs

    def _token_to_op(self, token_type: TokenType) -> str:
        """Map token type to operator string."""
        mapping = {
            TokenType.ADD: "+",
            TokenType.SUB: "-",
            TokenType.MUL: "*",
            TokenType.DIV: "/",
            TokenType.FLOORDIV: "//",
            TokenType.MOD: "%",
            TokenType.POW: "**",
            TokenType.TILDE: "~",  # String concatenation
        }
        op = mapping.get(token_type)
        if op is None:
            from bengal.rendering.kida.parser.errors import ParseError

            raise ParseError(f"Unmapped token type for binary operator: {token_type!r}")
        return op
