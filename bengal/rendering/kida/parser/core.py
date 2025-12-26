"""Core parser implementation for Kida.

Combines all parsing mixins into a single Parser class.
"""

from __future__ import annotations

from collections.abc import Sequence

from bengal.rendering.kida._types import Token
from bengal.rendering.kida.nodes import Template
from bengal.rendering.kida.parser.blocks import BlockParsingMixin
from bengal.rendering.kida.parser.expressions import ExpressionParsingMixin
from bengal.rendering.kida.parser.statements import StatementParsingMixin
from bengal.rendering.kida.parser.tokens import TokenNavigationMixin


class Parser(
    TokenNavigationMixin,
    BlockParsingMixin,
    StatementParsingMixin,
    ExpressionParsingMixin,
):
    """Parse tokens into Kida AST.

    Uses a stack-based approach for block tracking, enabling unified {% end %}
    syntax for all block types. When {% end %} is encountered, it always closes
    the innermost open block (like Go templates).

    Example:
        >>> tokens = tokenize("{{ name }}")
        >>> parser = Parser(tokens)
        >>> ast = parser.parse()
    """

    __slots__ = ("_tokens", "_pos", "_name", "_filename", "_source", "_autoescape", "_block_stack")

    def __init__(
        self,
        tokens: Sequence[Token],
        name: str | None = None,
        filename: str | None = None,
        source: str | None = None,
        autoescape: bool = True,
    ):
        self._tokens = tokens
        self._pos = 0
        self._name = name
        self._filename = filename
        self._source = source
        self._autoescape = autoescape
        self._block_stack: list[tuple[str, int, int]] = []  # (block_type, lineno, col)

    def parse(self) -> Template:
        """Parse tokens into Template AST."""
        body = self._parse_body()
        return Template(
            lineno=1,
            col_offset=0,
            body=tuple(body),
            extends=None,
        )
