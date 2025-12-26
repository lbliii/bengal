"""Kida Parser — transforms tokens into AST.

Recursive descent parser that builds an immutable AST
from the token stream produced by the lexer.

Features:
    - Pythonic scoping with let/set/export
    - Native async for loops
    - Rich error messages with suggestions
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bengal.rendering.kida._types import Token, TokenType
from bengal.rendering.kida.nodes import (
    Block,
    CondExpr,
    Const,
    Data,
    Dict,
    Export,
    Extends,
    Filter,
    For,
    FromImport,
    Getattr,
    Getitem,
    If,
    Include,
    Let,
    List,
    Macro,
    Name,
    Output,
    Set,
    Slice,
    Template,
    Test,
    Tuple,
    With,
)

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Expr, Node


class ParseError(Exception):
    """Parser error with location info."""

    def __init__(
        self,
        message: str,
        token: Token,
        suggestion: str | None = None,
    ):
        self.message = message
        self.token = token
        self.suggestion = suggestion
        super().__init__(self._format())

    def _format(self) -> str:
        msg = f"Parse error at line {self.token.lineno}: {self.message}"
        if self.suggestion:
            msg += f"\nSuggestion: {self.suggestion}"
        return msg


class Parser:
    """Parse tokens into Kida AST.

    Example:
        >>> tokens = tokenize("{{ name }}")
        >>> parser = Parser(tokens)
        >>> ast = parser.parse()
    """

    __slots__ = ("_tokens", "_pos", "_name", "_filename")

    def __init__(
        self,
        tokens: Sequence[Token],
        name: str | None = None,
        filename: str | None = None,
    ):
        self._tokens = tokens
        self._pos = 0
        self._name = name
        self._filename = filename

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
            raise ParseError(
                f"Expected {token_type.value}, got {self._current.type.value}",
                self._current,
            )
        return self._advance()

    def _match(self, *types: TokenType) -> bool:
        """Check if current token matches any of the types."""
        return self._current.type in types

    def parse(self) -> Template:
        """Parse tokens into Template AST."""
        body = self._parse_body()
        return Template(
            lineno=1,
            col_offset=0,
            body=tuple(body),
            extends=None,
        )

    def _parse_body(self, end_tokens: set[str] | None = None) -> list[Node]:
        """Parse template body until end token or EOF."""
        nodes: list[Node] = []
        end_tokens = end_tokens or set()

        while self._current.type != TokenType.EOF:
            # Check for block begin that might contain end token
            if self._current.type == TokenType.BLOCK_BEGIN:
                # Peek ahead to see if next token is an end token
                next_tok = self._peek(1)
                if next_tok.type == TokenType.NAME and next_tok.value in end_tokens:
                    # Don't consume the BLOCK_BEGIN, let parent handle it
                    break

                node = self._parse_block()
                if node is not None:
                    nodes.append(node)
            elif self._current.type == TokenType.DATA:
                nodes.append(self._parse_data())
            elif self._current.type == TokenType.VARIABLE_BEGIN:
                nodes.append(self._parse_output())
            elif self._current.type == TokenType.COMMENT_BEGIN:
                self._skip_comment()
            else:
                self._advance()

        return nodes

    def _parse_data(self) -> Data:
        """Parse raw text data."""
        token = self._advance()
        return Data(
            lineno=token.lineno,
            col_offset=token.col_offset,
            value=token.value,
        )

    def _parse_output(self) -> Output:
        """Parse {{ expression }}."""
        start = self._expect(TokenType.VARIABLE_BEGIN)
        expr = self._parse_expression()
        self._expect(TokenType.VARIABLE_END)

        return Output(
            lineno=start.lineno,
            col_offset=start.col_offset,
            expr=expr,
            escape=True,
        )

    def _parse_block(self) -> Node | None:
        """Parse {% ... %} block tag."""
        self._expect(TokenType.BLOCK_BEGIN)

        if self._current.type != TokenType.NAME:
            raise ParseError(
                "Expected block keyword",
                self._current,
            )

        keyword = self._current.value

        if keyword == "if":
            return self._parse_if()
        elif keyword == "for":
            return self._parse_for()
        elif keyword == "set":
            return self._parse_set()
        elif keyword == "let":
            return self._parse_let()
        elif keyword == "export":
            return self._parse_export()
        elif keyword == "block":
            return self._parse_block_tag()
        elif keyword == "extends":
            return self._parse_extends()
        elif keyword == "include":
            return self._parse_include()
        elif keyword == "macro":
            return self._parse_macro()
        elif keyword == "from":
            return self._parse_from_import()
        elif keyword == "with":
            return self._parse_with()
        elif keyword in ("endif", "endfor", "endblock", "endmacro", "endwith", "else", "elif"):
            # End/continuation tags handled by parent
            return None
        else:
            raise ParseError(
                f"Unknown block keyword: {keyword}",
                self._current,
            )

    def _parse_if(self) -> If:
        """Parse {% if %} ... {% endif %}."""
        start = self._advance()  # consume 'if'
        test = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        body = self._parse_body({"elif", "else", "endif"})

        elif_: list[tuple[Expr, Sequence[Node]]] = []
        else_: list[Node] = []

        # Now we're at {% elif/else/endif
        while self._current.type == TokenType.BLOCK_BEGIN:
            self._advance()  # consume {%
            keyword = self._current.value

            if keyword == "elif":
                self._advance()  # consume 'elif'
                elif_test = self._parse_expression()
                self._expect(TokenType.BLOCK_END)
                elif_body = self._parse_body({"elif", "else", "endif"})
                elif_.append((elif_test, tuple(elif_body)))
            elif keyword == "else":
                self._advance()  # consume 'else'
                self._expect(TokenType.BLOCK_END)
                else_ = self._parse_body({"endif"})
            elif keyword == "endif":
                self._advance()  # consume 'endif'
                self._expect(TokenType.BLOCK_END)
                break
            else:
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
        """Parse {% for %} ... {% endfor %}."""
        start = self._advance()  # consume 'for'

        # Parse target (loop variable)
        target = self._parse_primary()

        # Expect 'in'
        if self._current.type != TokenType.IN:
            raise ParseError(
                "Expected 'in' in for loop",
                self._current,
            )
        self._advance()

        # Parse iterable
        iter_expr = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        # Parse body
        body = self._parse_body({"else", "endfor"})

        else_: list[Node] = []

        # Now at {% else or {% endfor
        if self._current.type == TokenType.BLOCK_BEGIN:
            self._advance()  # consume {%
            keyword = self._current.value

            if keyword == "else":
                self._advance()  # consume 'else'
                self._expect(TokenType.BLOCK_END)
                else_ = self._parse_body({"endfor"})

                # Consume endfor
                if self._current.type == TokenType.BLOCK_BEGIN:
                    self._advance()
                    if self._current.value == "endfor":
                        self._advance()
                        self._expect(TokenType.BLOCK_END)
            elif keyword == "endfor":
                self._advance()  # consume 'endfor'
                self._expect(TokenType.BLOCK_END)

        return For(
            lineno=start.lineno,
            col_offset=start.col_offset,
            target=target,
            iter=iter_expr,
            body=tuple(body),
            else_=tuple(else_),
        )

    def _parse_set(self) -> Set:
        """Parse {% set x = expr %}."""
        start = self._advance()  # consume 'set'

        if self._current.type != TokenType.NAME:
            raise ParseError("Expected variable name", self._current)
        name = self._advance().value

        self._expect(TokenType.ASSIGN)
        value = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        return Set(
            lineno=start.lineno,
            col_offset=start.col_offset,
            name=name,
            value=value,
        )

    def _parse_let(self) -> Let:
        """Parse {% let x = expr %}."""
        start = self._advance()  # consume 'let'

        if self._current.type != TokenType.NAME:
            raise ParseError("Expected variable name", self._current)
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
            raise ParseError("Expected variable name", self._current)
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

    def _parse_block_tag(self) -> Block:
        """Parse {% block name %}...{% endblock %}."""
        start = self._advance()  # consume 'block'

        if self._current.type != TokenType.NAME:
            raise ParseError("Expected block name", self._current)
        name = self._advance().value

        self._expect(TokenType.BLOCK_END)
        body = self._parse_body({"endblock"})

        if self._current.value == "endblock":
            self._advance()
            self._expect(TokenType.BLOCK_END)

        return Block(
            lineno=start.lineno,
            col_offset=start.col_offset,
            name=name,
            body=tuple(body),
        )

    def _parse_extends(self) -> Extends:
        """Parse {% extends "base.html" %}."""
        start = self._advance()  # consume 'extends'
        template = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        return Extends(
            lineno=start.lineno,
            col_offset=start.col_offset,
            template=template,
        )

    def _parse_include(self) -> Include:
        """Parse {% include "partial.html" [with context] [ignore missing] %}."""
        start = self._advance()  # consume 'include'
        template = self._parse_expression()

        with_context = True
        ignore_missing = False

        # Parse optional modifiers
        while self._current.type == TokenType.NAME:
            keyword = self._current.value
            if keyword == "with":
                self._advance()  # consume 'with'
                if self._current.type == TokenType.NAME and self._current.value == "context":
                    self._advance()  # consume 'context'
                    with_context = True
                else:
                    raise ParseError("Expected 'context' after 'with'", self._current)
            elif keyword == "without":
                self._advance()  # consume 'without'
                if self._current.type == TokenType.NAME and self._current.value == "context":
                    self._advance()  # consume 'context'
                    with_context = False
                else:
                    raise ParseError("Expected 'context' after 'without'", self._current)
            elif keyword == "ignore":
                self._advance()  # consume 'ignore'
                if self._current.type == TokenType.NAME and self._current.value == "missing":
                    self._advance()  # consume 'missing'
                    ignore_missing = True
                else:
                    raise ParseError("Expected 'missing' after 'ignore'", self._current)
            else:
                break

        self._expect(TokenType.BLOCK_END)

        return Include(
            lineno=start.lineno,
            col_offset=start.col_offset,
            template=template,
            with_context=with_context,
            ignore_missing=ignore_missing,
        )

    def _parse_macro(self) -> Macro:
        """Parse {% macro name(args) %}...{% endmacro %}."""
        start = self._advance()  # consume 'macro'

        # Get macro name
        if self._current.type != TokenType.NAME:
            raise ParseError("Expected macro name", self._current)
        name = self._advance().value

        # Parse arguments
        args: list[str] = []
        defaults: list[Expr] = []

        self._expect(TokenType.LPAREN)
        while not self._match(TokenType.RPAREN):
            if args:
                self._expect(TokenType.COMMA)
            if self._current.type != TokenType.NAME:
                raise ParseError("Expected argument name", self._current)
            arg_name = self._advance().value
            args.append(arg_name)

            # Check for default value
            if self._match(TokenType.ASSIGN):
                self._advance()
                defaults.append(self._parse_expression())

        self._expect(TokenType.RPAREN)
        self._expect(TokenType.BLOCK_END)

        # Parse body until {% endmacro %}
        body: list[Node] = []
        while True:
            if self._match(TokenType.BLOCK_BEGIN):
                self._advance()
                if self._current.type == TokenType.NAME and self._current.value == "endmacro":
                    self._advance()  # consume 'endmacro'
                    self._expect(TokenType.BLOCK_END)
                    break
                else:
                    block_node = self._parse_block_content()
                    if block_node:
                        body.append(block_node)
            elif self._match(TokenType.VARIABLE_BEGIN):
                body.append(self._parse_output())
            elif self._match(TokenType.DATA):
                body.append(self._parse_data())
            elif self._match(TokenType.COMMENT_BEGIN):
                self._skip_comment()
            elif self._match(TokenType.EOF):
                raise ParseError("Unexpected end of template in macro", self._current)
            else:
                self._advance()

        return Macro(
            lineno=start.lineno,
            col_offset=start.col_offset,
            name=name,
            args=tuple(args),
            body=tuple(body),
            defaults=tuple(defaults),
        )

    def _parse_from_import(self) -> FromImport:
        """Parse {% from "template.html" import name1, name2 as alias %}."""
        start = self._advance()  # consume 'from'

        template = self._parse_expression()

        # Expect 'import'
        if self._current.type != TokenType.NAME or self._current.value != "import":
            raise ParseError("Expected 'import' after template name", self._current)
        self._advance()  # consume 'import'

        # Parse imported names
        names: list[tuple[str, str | None]] = []
        with_context = False

        while True:
            if self._current.type != TokenType.NAME:
                raise ParseError("Expected name to import", self._current)
            name = self._advance().value

            # Check for alias
            alias: str | None = None
            if self._current.type == TokenType.NAME and self._current.value == "as":
                self._advance()  # consume 'as'
                if self._current.type != TokenType.NAME:
                    raise ParseError("Expected alias name", self._current)
                alias = self._advance().value

            names.append((name, alias))

            # Check for comma or end
            if self._match(TokenType.COMMA):
                self._advance()
            elif self._current.type == TokenType.NAME and self._current.value == "with":
                self._advance()  # consume 'with'
                if self._current.type == TokenType.NAME and self._current.value == "context":
                    self._advance()  # consume 'context'
                    with_context = True
                break
            elif self._match(TokenType.BLOCK_END):
                break
            else:
                break

        self._expect(TokenType.BLOCK_END)

        return FromImport(
            lineno=start.lineno,
            col_offset=start.col_offset,
            template=template,
            names=tuple(names),
            with_context=with_context,
        )

    def _parse_with(self) -> Node:
        """Parse {% with var=value, ... %} ... {% endwith %}.

        Creates temporary variable bindings scoped to the with block.
        """

        start = self._advance()  # consume 'with'

        # Parse variable assignments
        assignments: list[tuple[str, Expr]] = []

        while True:
            if self._current.type != TokenType.NAME:
                raise ParseError("Expected variable name", self._current)
            name = self._advance().value

            self._expect(TokenType.ASSIGN)
            value = self._parse_expression()

            assignments.append((name, value))

            if not self._match(TokenType.COMMA):
                break
            self._advance()  # consume comma

        self._expect(TokenType.BLOCK_END)

        # Parse body until {% endwith %}
        body = self._parse_body({"endwith"})

        # Consume endwith
        if self._current.type == TokenType.BLOCK_BEGIN:
            self._advance()  # consume {%
            if self._current.type == TokenType.NAME and self._current.value == "endwith":
                self._advance()  # consume 'endwith'
                self._expect(TokenType.BLOCK_END)

        return With(
            lineno=start.lineno,
            col_offset=start.col_offset,
            targets=tuple(assignments),
            body=tuple(body),
        )

    def _skip_comment(self) -> None:
        """Skip comment block."""
        self._expect(TokenType.COMMENT_BEGIN)
        self._expect(TokenType.COMMENT_END)

    # Expression parsing

    def _parse_expression(self) -> Expr:
        """Parse expression with ternary.

        Filters are handled at higher precedence (in _parse_unary_postfix).
        """
        return self._parse_ternary()

    def _parse_ternary(self) -> Expr:
        """Parse ternary conditional: a if b else c

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

            # Expect "else"
            if self._current.type != TokenType.NAME or self._current.value != "else":
                raise ParseError("Expected 'else' in ternary expression", self._current)
            self._advance()  # consume "else"

            # Parse the "false" value (right-associative)
            else_expr = self._parse_ternary()

            return CondExpr(
                lineno=expr.lineno,
                col_offset=expr.col_offset,
                test=test,
                if_true=expr,
                if_false=else_expr,
            )

        return expr

    def _parse_or(self) -> Expr:
        """Parse 'or' expression."""
        return self._parse_binary(self._parse_and, TokenType.OR)

    def _parse_and(self) -> Expr:
        """Parse 'and' expression."""
        return self._parse_binary(self._parse_not, TokenType.AND)

    def _parse_not(self) -> Expr:
        """Parse 'not' expression."""
        from bengal.rendering.kida.nodes import UnaryOp

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
        from bengal.rendering.kida.nodes import Compare

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
        ):
            op_token = self._advance()
            op = op_token.value

            # Handle 'not in' and 'is not'
            if op == "not" and self._match(TokenType.IN):
                self._advance()
                op = "not in"
            elif op == "is" and self._match(TokenType.NOT):
                self._advance()
                op = "is not"

            # Handle tests: "is defined", "is not mapping", etc.
            if op in ("is", "is not"):
                # Check if next token is a test name (NAME token)
                if self._current.type == TokenType.NAME:
                    test_name = self._advance().value

                    # Parse optional arguments: is divisibleby(3)
                    test_args: list[Expr] = []
                    test_kwargs: dict[str, Expr] = {}
                    if self._match(TokenType.LPAREN):
                        self._advance()
                        test_args, test_kwargs = self._parse_call_args()
                        self._expect(TokenType.RPAREN)

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

    def _parse_addition(self) -> Expr:
        """Parse addition/subtraction/concatenation.

        The ~ operator is string concatenation in Jinja.
        """
        return self._parse_binary(
            self._parse_multiplication,
            TokenType.ADD,
            TokenType.SUB,
            TokenType.TILDE,
        )

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
        """Parse unary operators."""
        from bengal.rendering.kida.nodes import UnaryOp

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
        from bengal.rendering.kida.nodes import BinOp

        left = self._parse_postfix()

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

    def _parse_postfix(self) -> Expr:
        """Parse postfix operators (., [], (), |filter).

        Filters are parsed here (high precedence) so that:
        x | length == 0  parses as  (x | length) == 0
        """
        from bengal.rendering.kida.nodes import Call as KidaCall

        expr = self._parse_primary()

        while True:
            if self._match(TokenType.DOT):
                self._advance()
                if self._current.type != TokenType.NAME:
                    raise ParseError("Expected attribute name", self._current)
                attr = self._advance().value
                expr = Getattr(
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
            elif self._match(TokenType.LPAREN):
                self._advance()
                args, kwargs = self._parse_call_args()
                self._expect(TokenType.RPAREN)
                expr = KidaCall(
                    lineno=expr.lineno,
                    col_offset=expr.col_offset,
                    func=expr,
                    args=tuple(args),
                    kwargs=kwargs,
                )
            elif self._match(TokenType.PIPE):
                # Filter: expr | filter_name(args)
                self._advance()
                if self._current.type != TokenType.NAME:
                    raise ParseError("Expected filter name", self._current)
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
            else:
                break

        return expr

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
            if token.value == "true":
                return Const(token.lineno, token.col_offset, True)
            elif token.value == "false":
                return Const(token.lineno, token.col_offset, False)
            elif token.value == "none":
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

        raise ParseError(
            f"Unexpected token: {token.type.value}",
            token,
        )

    def _parse_binary(self, operand_parser, *op_types: TokenType) -> Expr:
        """Generic binary expression parser."""
        from bengal.rendering.kida.nodes import BinOp, BoolOp

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
        }
        return mapping.get(token_type, "+")
