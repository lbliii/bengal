"""Jinja2 Compatibility Layer for Kida.

This module provides a parser that accepts Jinja2 syntax and produces
Kida AST. This enables:

1. Benchmarking Kida's runtime against Jinja2 using existing templates
2. Gradual migration from Jinja2 to Kida
3. Running existing template test suites

Syntax Translations:
    Jinja2                      Kida Native
    ──────────────────────────  ────────────────────
    {% endif %}                 {% end %}
    {% endfor %}                {% end %}
    {% endblock %}              {% end %}
    {% endmacro %}              {% end %}
    {% macro foo() %}           {% def foo() %}
    {% else %} (in for)         {% empty %}
    {{ x | a | b | c }}         {{ x |> a |> b |> c }}

The Kida AST is engine-agnostic - the compiler and runtime don't care
whether it came from Jinja syntax or Kida-native syntax.

Example:
    >>> from kida.compat.jinja import JinjaCompatEnvironment
    >>> env = JinjaCompatEnvironment(loader=FileSystemLoader("templates"))
    >>> template = env.get_template("base.html")  # Jinja2 syntax
    >>> html = template.render(page=page)  # Kida runtime
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bengal.rendering.kida._types import Token, TokenType
from bengal.rendering.kida.nodes import (
    Block,
    Capture,
    CondExpr,
    Const,
    Data,
    Def,
    Dict,
    Export,
    Extends,
    Filter,
    For,
    FromImport,
    FuncCall,
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
    Template,
    Test,
    Tuple,
    With,
)

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Expr, Node


class JinjaParseError(Exception):
    """Parser error with rich source context."""

    def __init__(
        self,
        message: str,
        token: Token,
        source: str | None = None,
        filename: str | None = None,
        suggestion: str | None = None,
    ):
        self.message = message
        self.token = token
        self.source = source
        self.filename = filename
        self.suggestion = suggestion
        super().__init__(self._format())

    def _format(self) -> str:
        location = self.filename or "<template>"
        header = f"Jinja Parse Error: {self.message}\n  --> {location}:{self.token.lineno}:{self.token.col_offset}"

        if self.source:
            lines = self.source.splitlines()
            if 0 < self.token.lineno <= len(lines):
                error_line = lines[self.token.lineno - 1]
                pointer = " " * self.token.col_offset + "^"
                line_num = self.token.lineno
                msg = f"""
{header}
   |
{line_num:>3} | {error_line}
   | {pointer}"""
            else:
                msg = f"\n{header}"
        else:
            msg = f"\n{header}"

        if self.suggestion:
            msg += f"\n\nSuggestion: {self.suggestion}"

        return msg


class JinjaParser:
    """Parse Jinja2 syntax into Kida AST.

    This parser accepts Jinja2 template syntax and produces Kida AST nodes.
    The AST can then be compiled and rendered using Kida's fast runtime.

    Supported Jinja2 features:
        - {{ expressions }}
        - {% if %}...{% elif %}...{% else %}...{% endif %}
        - {% for x in items %}...{% else %}...{% endfor %}
        - {% block name %}...{% endblock %}
        - {% extends "base.html" %}
        - {% include "partial.html" %}
        - {% macro name(args) %}...{% endmacro %}
        - {% from "x.html" import a, b %}
        - {% set x = expr %}
        - {% with x = expr %}...{% endwith %}
        - Filters: {{ x | filter(args) }}
        - Tests: {% if x is defined %}

    Example:
        >>> tokens = list(Lexer(jinja_source, config).tokenize())
        >>> parser = JinjaParser(tokens, source=jinja_source)
        >>> kida_ast = parser.parse()
    """

    __slots__ = ("_tokens", "_pos", "_name", "_filename", "_source")

    # Jinja2 block end tokens → Kida's unified {% end %}
    JINJA_END_TOKENS = frozenset(
        {
            "endif",
            "endfor",
            "endblock",
            "endmacro",
            "endwith",
            "endfilter",
            "endautoescape",
            "endcall",
            "endraw",
            "endset",
        }
    )

    def __init__(
        self,
        tokens: Sequence[Token],
        name: str | None = None,
        filename: str | None = None,
        source: str | None = None,
    ):
        self._tokens = tokens
        self._pos = 0
        self._name = name
        self._filename = filename
        self._source = source

    def _error(
        self,
        message: str,
        token: Token | None = None,
        suggestion: str | None = None,
    ) -> JinjaParseError:
        return JinjaParseError(
            message=message,
            token=token or self._current,
            source=self._source,
            filename=self._filename,
            suggestion=suggestion,
        )

    @property
    def _current(self) -> Token:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return Token(TokenType.EOF, "", 0, 0)

    def _peek(self, offset: int = 0) -> Token:
        pos = self._pos + offset
        if pos < len(self._tokens):
            return self._tokens[pos]
        return Token(TokenType.EOF, "", 0, 0)

    def _advance(self) -> Token:
        token = self._current
        self._pos += 1
        return token

    def _expect(self, token_type: TokenType) -> Token:
        if self._current.type != token_type:
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
        return self._current.type in types

    def _is_jinja_end_token(self, value: str) -> bool:
        """Check if value is a Jinja2 block-ending keyword."""
        return value in self.JINJA_END_TOKENS

    def parse(self) -> Template:
        """Parse Jinja2 tokens into Kida Template AST."""
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
            # Check for Jinja end tokens
            if self._current.type == TokenType.BLOCK_START:
                next_token = self._peek(1)
                if next_token.type == TokenType.NAME:
                    if next_token.value in end_tokens:
                        break
                    # Convert Jinja end tokens to signal block end
                    if self._is_jinja_end_token(next_token.value):
                        break

            node = self._parse_node()
            if node is not None:
                nodes.append(node)

        return nodes

    def _parse_node(self) -> Node | None:
        """Parse a single node."""
        token = self._current

        if token.type == TokenType.DATA:
            self._advance()
            if token.value:
                return Data(lineno=token.lineno, col_offset=token.col_offset, value=token.value)
            return None

        if token.type == TokenType.VARIABLE_START:
            return self._parse_output()

        if token.type == TokenType.BLOCK_START:
            return self._parse_block()

        if token.type == TokenType.COMMENT_START:
            return self._parse_comment()

        self._advance()
        return None

    def _parse_output(self) -> Output:
        """Parse {{ expression }}."""
        start = self._expect(TokenType.VARIABLE_START)
        expr = self._parse_expression()
        self._expect(TokenType.VARIABLE_END)
        return Output(lineno=start.lineno, col_offset=start.col_offset, expr=expr)

    def _parse_block(self) -> Node | None:
        """Parse {% ... %}."""
        start = self._expect(TokenType.BLOCK_START)

        if self._current.type != TokenType.NAME:
            raise self._error("Expected block name")

        name = self._current.value
        self._advance()

        # Dispatch to specific block handlers
        handlers = {
            "if": self._parse_if,
            "for": self._parse_for,
            "block": self._parse_block_def,
            "extends": self._parse_extends,
            "include": self._parse_include,
            "set": self._parse_set,
            "let": self._parse_let,
            "export": self._parse_export,
            "with": self._parse_with,
            "macro": self._parse_macro,
            "from": self._parse_from_import,
            "import": self._parse_import,
            "raw": self._parse_raw,
        }

        handler = handlers.get(name)
        if handler:
            return handler(start)

        # Unknown block - skip to end
        self._expect(TokenType.BLOCK_END)
        return None

    def _parse_if(self, start: Token) -> If:
        """Parse {% if %}...{% elif %}...{% else %}...{% endif %}."""
        test = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        body = self._parse_body({"elif", "else", "endif"})
        elif_: list[tuple[Expr, Sequence[Node]]] = []
        else_: list[Node] = []

        while self._current.type == TokenType.BLOCK_START:
            self._advance()
            if self._current.type != TokenType.NAME:
                break

            keyword = self._current.value
            self._advance()

            if keyword == "elif":
                elif_test = self._parse_expression()
                self._expect(TokenType.BLOCK_END)
                elif_body = self._parse_body({"elif", "else", "endif"})
                elif_.append((elif_test, tuple(elif_body)))
            elif keyword == "else":
                self._expect(TokenType.BLOCK_END)
                else_ = self._parse_body({"endif"})
            elif keyword == "endif":
                self._expect(TokenType.BLOCK_END)
                break

        return If(
            lineno=start.lineno,
            col_offset=start.col_offset,
            test=test,
            body=tuple(body),
            elif_=tuple(elif_),
            else_=tuple(else_),
        )

    def _parse_for(self, start: Token) -> For:
        """Parse {% for x in items %}...{% else %}...{% endfor %}."""
        target = self._parse_assignment_target()

        if self._current.type != TokenType.NAME or self._current.value != "in":
            raise self._error("Expected 'in' in for loop")
        self._advance()

        iter_expr = self._parse_expression()

        # Optional 'if' filter
        test = None
        if self._current.type == TokenType.NAME and self._current.value == "if":
            self._advance()
            test = self._parse_expression()

        # Optional 'recursive'
        recursive = False
        if self._current.type == TokenType.NAME and self._current.value == "recursive":
            self._advance()
            recursive = True

        self._expect(TokenType.BLOCK_END)

        body = self._parse_body({"else", "endfor"})
        empty: list[Node] = []

        if self._current.type == TokenType.BLOCK_START:
            self._advance()
            if self._current.type == TokenType.NAME and self._current.value == "else":
                self._advance()
                self._expect(TokenType.BLOCK_END)
                empty = self._parse_body({"endfor"})

            if self._current.type == TokenType.BLOCK_START:
                self._advance()

            if self._current.type == TokenType.NAME and self._current.value == "endfor":
                self._advance()
                self._expect(TokenType.BLOCK_END)

        return For(
            lineno=start.lineno,
            col_offset=start.col_offset,
            target=target,
            iter=iter_expr,
            body=tuple(body),
            empty=tuple(empty),  # Kida uses 'empty', mapped from Jinja's 'else'
            recursive=recursive,
            test=test,
        )

    def _parse_block_def(self, start: Token) -> Block:
        """Parse {% block name %}...{% endblock %}."""
        if self._current.type != TokenType.NAME:
            raise self._error("Expected block name")

        name = self._current.value
        self._advance()

        # Optional 'scoped' or 'required'
        scoped = False
        required = False
        while self._current.type == TokenType.NAME:
            if self._current.value == "scoped":
                scoped = True
                self._advance()
            elif self._current.value == "required":
                required = True
                self._advance()
            else:
                break

        self._expect(TokenType.BLOCK_END)

        body = self._parse_body({"endblock"})
        self._consume_jinja_end("endblock")

        return Block(
            lineno=start.lineno,
            col_offset=start.col_offset,
            name=name,
            body=tuple(body),
            scoped=scoped,
            required=required,
        )

    def _parse_extends(self, start: Token) -> Extends:
        """Parse {% extends "base.html" %}."""
        template = self._parse_expression()
        self._expect(TokenType.BLOCK_END)
        return Extends(lineno=start.lineno, col_offset=start.col_offset, template=template)

    def _parse_include(self, start: Token) -> Include:
        """Parse {% include "partial.html" %}."""
        template = self._parse_expression()

        with_context = True
        ignore_missing = False

        while self._current.type == TokenType.NAME:
            if self._current.value == "without":
                self._advance()
                if self._current.type == TokenType.NAME and self._current.value == "context":
                    self._advance()
                    with_context = False
            elif self._current.value == "with":
                self._advance()
                if self._current.type == TokenType.NAME and self._current.value == "context":
                    self._advance()
                    with_context = True
            elif self._current.value == "ignore":
                self._advance()
                if self._current.type == TokenType.NAME and self._current.value == "missing":
                    self._advance()
                    ignore_missing = True
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

    def _parse_set(self, start: Token) -> Set | Capture:
        """Parse {% set x = expr %} or {% set x %}...{% endset %}."""
        if self._current.type != TokenType.NAME:
            raise self._error("Expected variable name")

        name = self._current.value
        self._advance()

        # Check for block capture: {% set x %}...{% endset %}
        if self._current.type == TokenType.BLOCK_END:
            self._advance()
            body = self._parse_body({"endset"})
            self._consume_jinja_end("endset")
            return Capture(
                lineno=start.lineno,
                col_offset=start.col_offset,
                name=name,
                body=tuple(body),
            )

        # Regular set: {% set x = expr %}
        if self._current.type == TokenType.ASSIGN:
            self._advance()

        value = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        return Set(lineno=start.lineno, col_offset=start.col_offset, name=name, value=value)

    def _parse_let(self, start: Token) -> Let:
        """Parse {% let x = expr %}."""
        if self._current.type != TokenType.NAME:
            raise self._error("Expected variable name")

        name = self._current.value
        self._advance()

        if self._current.type == TokenType.ASSIGN:
            self._advance()

        value = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        return Let(lineno=start.lineno, col_offset=start.col_offset, name=name, value=value)

    def _parse_export(self, start: Token) -> Export:
        """Parse {% export x = expr %}."""
        if self._current.type != TokenType.NAME:
            raise self._error("Expected variable name")

        name = self._current.value
        self._advance()

        if self._current.type == TokenType.ASSIGN:
            self._advance()

        value = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        return Export(lineno=start.lineno, col_offset=start.col_offset, name=name, value=value)

    def _parse_with(self, start: Token) -> With:
        """Parse {% with x = expr %}...{% endwith %}."""
        targets: list[tuple[str, Expr]] = []

        while True:
            if self._current.type != TokenType.NAME:
                break

            name = self._current.value
            self._advance()

            if self._current.type == TokenType.ASSIGN:
                self._advance()

            value = self._parse_expression()
            targets.append((name, value))

            if self._current.type == TokenType.COMMA:
                self._advance()
            else:
                break

        self._expect(TokenType.BLOCK_END)

        body = self._parse_body({"endwith"})
        self._consume_jinja_end("endwith")

        return With(
            lineno=start.lineno,
            col_offset=start.col_offset,
            targets=tuple(targets),
            body=tuple(body),
        )

    def _parse_macro(self, start: Token) -> Macro | Def:
        """Parse {% macro name(args) %}...{% endmacro %}.

        Produces Macro node for Jinja compatibility. The compiler can
        handle both Macro and Def nodes identically.
        """
        if self._current.type != TokenType.NAME:
            raise self._error("Expected macro name")

        name = self._current.value
        self._advance()

        args, defaults = self._parse_signature()
        self._expect(TokenType.BLOCK_END)

        body = self._parse_body({"endmacro"})
        self._consume_jinja_end("endmacro")

        # Return Macro for now (could return Def if we want to normalize)
        return Macro(
            lineno=start.lineno,
            col_offset=start.col_offset,
            name=name,
            args=tuple(args),
            body=tuple(body),
            defaults=tuple(defaults),
        )

    def _parse_from_import(self, start: Token) -> FromImport:
        """Parse {% from "x.html" import a, b as c %}."""
        template = self._parse_expression()

        if self._current.type != TokenType.NAME or self._current.value != "import":
            raise self._error("Expected 'import' after template path")
        self._advance()

        names: list[tuple[str, str | None]] = []
        while True:
            if self._current.type != TokenType.NAME:
                break

            name = self._current.value
            self._advance()

            alias = None
            if self._current.type == TokenType.NAME and self._current.value == "as":
                self._advance()
                if self._current.type == TokenType.NAME:
                    alias = self._current.value
                    self._advance()

            names.append((name, alias))

            if self._current.type == TokenType.COMMA:
                self._advance()
            else:
                break

        with_context = False
        if self._current.type == TokenType.NAME and self._current.value == "with":
            self._advance()
            if self._current.type == TokenType.NAME and self._current.value == "context":
                self._advance()
                with_context = True

        self._expect(TokenType.BLOCK_END)

        return FromImport(
            lineno=start.lineno,
            col_offset=start.col_offset,
            template=template,
            names=tuple(names),
            with_context=with_context,
        )

    def _parse_import(self, start: Token) -> FromImport:
        """Parse {% import "x.html" as name %}."""
        template = self._parse_expression()

        if self._current.type != TokenType.NAME or self._current.value != "as":
            raise self._error("Expected 'as' after template path")
        self._advance()

        if self._current.type != TokenType.NAME:
            raise self._error("Expected name after 'as'")

        name = self._current.value
        self._advance()

        with_context = False
        if self._current.type == TokenType.NAME and self._current.value == "with":
            self._advance()
            if self._current.type == TokenType.NAME and self._current.value == "context":
                self._advance()
                with_context = True

        self._expect(TokenType.BLOCK_END)

        # Import as single-name FromImport
        return FromImport(
            lineno=start.lineno,
            col_offset=start.col_offset,
            template=template,
            names=((name, None),),
            with_context=with_context,
        )

    def _parse_raw(self, start: Token) -> Data:
        """Parse {% raw %}...{% endraw %}."""
        self._expect(TokenType.BLOCK_END)

        # Collect raw content
        content_parts = []
        while self._current.type != TokenType.EOF:
            if self._current.type == TokenType.BLOCK_START:
                next_tok = self._peek(1)
                if next_tok.type == TokenType.NAME and next_tok.value == "endraw":
                    break
            content_parts.append(self._current.value)
            self._advance()

        self._consume_jinja_end("endraw")

        return Data(
            lineno=start.lineno,
            col_offset=start.col_offset,
            value="".join(content_parts),
        )

    def _parse_comment(self) -> None:
        """Parse {# comment #}."""
        while self._current.type != TokenType.COMMENT_END and self._current.type != TokenType.EOF:
            self._advance()
        if self._current.type == TokenType.COMMENT_END:
            self._advance()
        return None

    def _consume_jinja_end(self, end_name: str) -> None:
        """Consume a Jinja end block like {% endif %}."""
        if self._current.type == TokenType.BLOCK_START:
            self._advance()
            if self._current.type == TokenType.NAME and self._current.value == end_name:
                self._advance()
                self._expect(TokenType.BLOCK_END)

    def _parse_signature(self) -> tuple[list[str], list[Expr]]:
        """Parse function/macro signature: (arg1, arg2=default)."""
        args: list[str] = []
        defaults: list[Expr] = []

        if self._current.type != TokenType.LPAREN:
            return args, defaults

        self._advance()

        while self._current.type != TokenType.RPAREN:
            if self._current.type != TokenType.NAME:
                break

            name = self._current.value
            args.append(name)
            self._advance()

            if self._current.type == TokenType.ASSIGN:
                self._advance()
                default = self._parse_expression()
                defaults.append(default)

            if self._current.type == TokenType.COMMA:
                self._advance()
            else:
                break

        if self._current.type == TokenType.RPAREN:
            self._advance()

        return args, defaults

    def _parse_assignment_target(self) -> Expr:
        """Parse assignment target (variable or tuple)."""
        return self._parse_tuple_or_name()

    def _parse_tuple_or_name(self) -> Expr:
        """Parse tuple unpacking or single name."""
        first = self._parse_primary()

        if self._current.type == TokenType.COMMA:
            items = [first]
            while self._current.type == TokenType.COMMA:
                self._advance()
                items.append(self._parse_primary())
            return Tuple(
                lineno=first.lineno,
                col_offset=first.col_offset,
                items=tuple(items),
                ctx="store",
            )

        return first

    # =========================================================================
    # Expression Parsing
    # =========================================================================

    def _parse_expression(self) -> Expr:
        """Parse a complete expression."""
        return self._parse_conditional()

    def _parse_conditional(self) -> Expr:
        """Parse conditional expression: a if cond else b."""
        expr = self._parse_or()

        if self._current.type == TokenType.NAME and self._current.value == "if":
            self._advance()
            test = self._parse_or()

            if self._current.type == TokenType.NAME and self._current.value == "else":
                self._advance()
                if_false = self._parse_conditional()
            else:
                if_false = Const(lineno=expr.lineno, col_offset=expr.col_offset, value=None)

            return CondExpr(
                lineno=expr.lineno,
                col_offset=expr.col_offset,
                test=test,
                if_true=expr,
                if_false=if_false,
            )

        return expr

    def _parse_or(self) -> Expr:
        """Parse 'or' expressions."""
        left = self._parse_and()

        while self._current.type == TokenType.NAME and self._current.value == "or":
            self._advance()
            right = self._parse_and()
            from bengal.rendering.kida.nodes import BoolOp

            left = BoolOp(
                lineno=left.lineno,
                col_offset=left.col_offset,
                op="or",
                values=(left, right),
            )

        return left

    def _parse_and(self) -> Expr:
        """Parse 'and' expressions."""
        left = self._parse_not()

        while self._current.type == TokenType.NAME and self._current.value == "and":
            self._advance()
            right = self._parse_not()
            from bengal.rendering.kida.nodes import BoolOp

            left = BoolOp(
                lineno=left.lineno,
                col_offset=left.col_offset,
                op="and",
                values=(left, right),
            )

        return left

    def _parse_not(self) -> Expr:
        """Parse 'not' expressions."""
        if self._current.type == TokenType.NAME and self._current.value == "not":
            start = self._advance()
            operand = self._parse_not()
            from bengal.rendering.kida.nodes import UnaryOp

            return UnaryOp(
                lineno=start.lineno,
                col_offset=start.col_offset,
                op="not",
                operand=operand,
            )

        return self._parse_compare()

    def _parse_compare(self) -> Expr:
        """Parse comparison expressions."""
        left = self._parse_add()
        ops: list[str] = []
        comparators: list[Expr] = []

        while True:
            op = None
            if self._current.type in (
                TokenType.EQ,
                TokenType.NE,
                TokenType.LT,
                TokenType.LE,
                TokenType.GT,
                TokenType.GE,
            ):
                op = self._current.value
                self._advance()
            elif self._current.type == TokenType.NAME:
                if self._current.value == "in":
                    op = "in"
                    self._advance()
                elif self._current.value == "not":
                    self._advance()
                    if self._current.type == TokenType.NAME and self._current.value == "in":
                        op = "not in"
                        self._advance()
                    else:
                        # Not a comparison, restore position
                        self._pos -= 1
                        break
                elif self._current.value == "is":
                    self._advance()
                    if self._current.type == TokenType.NAME and self._current.value == "not":
                        op = "is not"
                        self._advance()
                    else:
                        op = "is"
                else:
                    break
            else:
                break

            if op:
                # Handle 'is' test specially
                if op in ("is", "is not"):
                    return self._parse_test(left, negated=(op == "is not"))

                ops.append(op)
                comparators.append(self._parse_add())

        if ops:
            from bengal.rendering.kida.nodes import Compare

            return Compare(
                lineno=left.lineno,
                col_offset=left.col_offset,
                left=left,
                ops=tuple(ops),
                comparators=tuple(comparators),
            )

        return left

    def _parse_test(self, value: Expr, negated: bool = False) -> Test:
        """Parse 'is' test expression."""
        if self._current.type != TokenType.NAME:
            raise self._error("Expected test name")

        name = self._current.value
        self._advance()

        args: list[Expr] = []
        kwargs: dict[str, Expr] = {}

        if self._current.type == TokenType.LPAREN:
            self._advance()
            args, kwargs = self._parse_arguments()
            self._expect(TokenType.RPAREN)

        return Test(
            lineno=value.lineno,
            col_offset=value.col_offset,
            value=value,
            name=name,
            args=tuple(args),
            kwargs=kwargs,
            negated=negated,
        )

    def _parse_add(self) -> Expr:
        """Parse + and - expressions."""
        left = self._parse_mul()

        while self._current.type in (TokenType.PLUS, TokenType.MINUS):
            op = self._current.value
            self._advance()
            right = self._parse_mul()
            from bengal.rendering.kida.nodes import BinOp

            left = BinOp(
                lineno=left.lineno,
                col_offset=left.col_offset,
                op=op,
                left=left,
                right=right,
            )

        return left

    def _parse_mul(self) -> Expr:
        """Parse *, /, //, % expressions."""
        left = self._parse_unary()

        while self._current.type in (
            TokenType.MUL,
            TokenType.DIV,
            TokenType.FLOORDIV,
            TokenType.MOD,
        ):
            op = self._current.value
            self._advance()
            right = self._parse_unary()
            from bengal.rendering.kida.nodes import BinOp

            left = BinOp(
                lineno=left.lineno,
                col_offset=left.col_offset,
                op=op,
                left=left,
                right=right,
            )

        return left

    def _parse_unary(self) -> Expr:
        """Parse unary expressions: -x, +x."""
        if self._current.type in (TokenType.PLUS, TokenType.MINUS):
            op = self._current.value
            start = self._advance()
            operand = self._parse_unary()
            from bengal.rendering.kida.nodes import UnaryOp

            return UnaryOp(
                lineno=start.lineno,
                col_offset=start.col_offset,
                op=op,
                operand=operand,
            )

        return self._parse_pow()

    def _parse_pow(self) -> Expr:
        """Parse power expression: x ** y."""
        left = self._parse_filter()

        if self._current.type == TokenType.POW:
            self._advance()
            right = self._parse_unary()
            from bengal.rendering.kida.nodes import BinOp

            return BinOp(
                lineno=left.lineno,
                col_offset=left.col_offset,
                op="**",
                left=left,
                right=right,
            )

        return left

    def _parse_filter(self) -> Expr:
        """Parse filter expressions: x | filter1 | filter2(arg)."""
        value = self._parse_postfix()

        while self._current.type == TokenType.PIPE:
            self._advance()

            if self._current.type != TokenType.NAME:
                raise self._error("Expected filter name after '|'")

            name = self._current.value
            self._advance()

            args: list[Expr] = []
            kwargs: dict[str, Expr] = {}

            if self._current.type == TokenType.LPAREN:
                self._advance()
                args, kwargs = self._parse_arguments()
                self._expect(TokenType.RPAREN)

            value = Filter(
                lineno=value.lineno,
                col_offset=value.col_offset,
                value=value,
                name=name,
                args=tuple(args),
                kwargs=kwargs,
            )

        return value

    def _parse_postfix(self) -> Expr:
        """Parse postfix expressions: x.attr, x[key], x(args)."""
        expr = self._parse_primary()

        while True:
            if self._current.type == TokenType.DOT:
                self._advance()
                if self._current.type != TokenType.NAME:
                    raise self._error("Expected attribute name after '.'")
                attr = self._current.value
                self._advance()
                expr = Getattr(lineno=expr.lineno, col_offset=expr.col_offset, obj=expr, attr=attr)

            elif self._current.type == TokenType.LBRACKET:
                self._advance()
                key = self._parse_expression()
                self._expect(TokenType.RBRACKET)
                expr = Getitem(lineno=expr.lineno, col_offset=expr.col_offset, obj=expr, key=key)

            elif self._current.type == TokenType.LPAREN:
                self._advance()
                args, kwargs = self._parse_arguments()
                self._expect(TokenType.RPAREN)
                expr = FuncCall(
                    lineno=expr.lineno,
                    col_offset=expr.col_offset,
                    func=expr,
                    args=tuple(args),
                    kwargs=kwargs,
                )

            else:
                break

        return expr

    def _parse_primary(self) -> Expr:
        """Parse primary expressions: literals, names, lists, dicts, tuples."""
        token = self._current

        if token.type == TokenType.NAME:
            self._advance()
            # Handle special constants
            if token.value == "true" or token.value == "True":
                return Const(lineno=token.lineno, col_offset=token.col_offset, value=True)
            if token.value == "false" or token.value == "False":
                return Const(lineno=token.lineno, col_offset=token.col_offset, value=False)
            if token.value == "none" or token.value == "None":
                return Const(lineno=token.lineno, col_offset=token.col_offset, value=None)
            return Name(lineno=token.lineno, col_offset=token.col_offset, name=token.value)

        if token.type == TokenType.STRING:
            self._advance()
            return Const(lineno=token.lineno, col_offset=token.col_offset, value=token.value)

        if token.type == TokenType.INTEGER:
            self._advance()
            return Const(lineno=token.lineno, col_offset=token.col_offset, value=int(token.value))

        if token.type == TokenType.FLOAT:
            self._advance()
            return Const(lineno=token.lineno, col_offset=token.col_offset, value=float(token.value))

        if token.type == TokenType.LPAREN:
            return self._parse_tuple_or_parens()

        if token.type == TokenType.LBRACKET:
            return self._parse_list()

        if token.type == TokenType.LBRACE:
            return self._parse_dict()

        raise self._error(f"Unexpected token: {token.type.value}")

    def _parse_tuple_or_parens(self) -> Expr:
        """Parse (expr) or (a, b, c)."""
        self._expect(TokenType.LPAREN)

        if self._current.type == TokenType.RPAREN:
            self._advance()
            return Tuple(lineno=self._current.lineno, col_offset=self._current.col_offset, items=())

        first = self._parse_expression()

        if self._current.type == TokenType.COMMA:
            items = [first]
            while self._current.type == TokenType.COMMA:
                self._advance()
                if self._current.type == TokenType.RPAREN:
                    break
                items.append(self._parse_expression())
            self._expect(TokenType.RPAREN)
            return Tuple(lineno=first.lineno, col_offset=first.col_offset, items=tuple(items))

        self._expect(TokenType.RPAREN)
        return first

    def _parse_list(self) -> List:
        """Parse [a, b, c]."""
        start = self._expect(TokenType.LBRACKET)
        items: list[Expr] = []

        while self._current.type != TokenType.RBRACKET:
            items.append(self._parse_expression())
            if self._current.type == TokenType.COMMA:
                self._advance()
            else:
                break

        self._expect(TokenType.RBRACKET)
        return List(lineno=start.lineno, col_offset=start.col_offset, items=tuple(items))

    def _parse_dict(self) -> Dict:
        """Parse {a: b, c: d}."""
        start = self._expect(TokenType.LBRACE)
        keys: list[Expr] = []
        values: list[Expr] = []

        while self._current.type != TokenType.RBRACE:
            key = self._parse_expression()
            self._expect(TokenType.COLON)
            value = self._parse_expression()
            keys.append(key)
            values.append(value)
            if self._current.type == TokenType.COMMA:
                self._advance()
            else:
                break

        self._expect(TokenType.RBRACE)
        return Dict(
            lineno=start.lineno,
            col_offset=start.col_offset,
            keys=tuple(keys),
            values=tuple(values),
        )

    def _parse_arguments(self) -> tuple[list[Expr], dict[str, Expr]]:
        """Parse function call arguments: arg1, arg2, kwarg=value."""
        args: list[Expr] = []
        kwargs: dict[str, Expr] = {}

        while self._current.type not in (TokenType.RPAREN, TokenType.EOF):
            # Check for keyword argument
            if self._current.type == TokenType.NAME and self._peek(1).type == TokenType.ASSIGN:
                name = self._current.value
                self._advance()
                self._advance()  # Skip '='
                value = self._parse_expression()
                kwargs[name] = value
            else:
                args.append(self._parse_expression())

            if self._current.type == TokenType.COMMA:
                self._advance()
            else:
                break

        return args, kwargs
