"""Special block parsing for Kida parser.

Provides mixin for parsing special blocks (with, do, raw, capture, cache, filter_block).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.kida._types import TokenType
from bengal.rendering.kida.nodes import (
    Cache,
    Capture,
    Const,
    Do,
    Filter,
    FilterBlock,
    Raw,
    With,
)

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Expr, Node

from bengal.rendering.kida.parser.blocks.core import BlockStackMixin


class SpecialBlockParsingMixin(BlockStackMixin):
    """Mixin for parsing special blocks.

    Required Host Attributes:
        - All from BlockStackMixin
        - All from TokenNavigationMixin
        - _parse_body: method
        - _parse_expression: method
        - _parse_call_args: method
        - _peek: method
        - _match: method
        - _advance: method
        - _expect: method
        - _error: method
    """

    def _parse_with(self) -> Node:
        """Parse {% with var=value, ... %} ... {% end %} or {% endwith %.

        Creates temporary variable bindings scoped to the with block.
        """
        start = self._advance()  # consume 'with'
        self._push_block("with", start)

        # Parse variable assignments
        assignments: list[tuple[str, Expr]] = []

        while True:
            if self._current.type != TokenType.NAME:
                raise self._error("Expected variable name")
            name = self._advance().value

            self._expect(TokenType.ASSIGN)
            value = self._parse_expression()

            assignments.append((name, value))

            if not self._match(TokenType.COMMA):
                break
            self._advance()  # consume comma

        self._expect(TokenType.BLOCK_END)

        # Parse body
        body = self._parse_body()

        # Consume end tag
        self._consume_end_tag("with")

        return With(
            lineno=start.lineno,
            col_offset=start.col_offset,
            targets=tuple(assignments),
            body=tuple(body),
        )

    def _parse_do(self) -> Do:
        """Parse {% do expr %.

        Expression statement for side effects (e.g., list.append).
        The result is discarded.
        """
        start = self._advance()  # consume 'do'
        expr = self._parse_expression()
        self._expect(TokenType.BLOCK_END)

        return Do(
            lineno=start.lineno,
            col_offset=start.col_offset,
            expr=expr,
        )

    def _parse_raw(self) -> Raw:
        """Parse {% raw %}...{% endraw %.

        Raw block that prevents template processing of its content.
        """
        start = self._advance()  # consume 'raw'
        self._expect(TokenType.BLOCK_END)

        # Collect all content until {% endraw %}
        content_parts: list[str] = []

        while True:
            if self._current.type == TokenType.EOF:
                raise self._error("Unclosed raw block", token=start)

            if self._current.type == TokenType.BLOCK_BEGIN:
                # Peek ahead to see if this is {% endraw %}
                self._advance()  # consume {%
                if self._current.type == TokenType.NAME and self._current.value == "endraw":
                    self._advance()  # consume 'endraw'
                    self._expect(TokenType.BLOCK_END)
                    break
                else:
                    # Not endraw, include the block as literal text
                    # We already consumed BLOCK_BEGIN and are at NAME token
                    # Build: {% name %} or {% name args %}
                    content_parts.append("{%")
                    # Collect tokens until BLOCK_END
                    while (
                        self._current.type != TokenType.BLOCK_END
                        and self._current.type != TokenType.EOF
                    ):
                        if self._current.value:
                            content_parts.append(" ")
                            content_parts.append(str(self._current.value))
                        self._advance()
                    if self._current.type == TokenType.BLOCK_END:
                        content_parts.append(" %}")
                        self._advance()
            elif self._current.type == TokenType.DATA:
                content_parts.append(self._current.value)
                self._advance()
            elif self._current.type == TokenType.VARIABLE_BEGIN:
                content_parts.append("{{")
                self._advance()
                # Capture expression tokens until VARIABLE_END
                while (
                    self._current.type != TokenType.VARIABLE_END
                    and self._current.type != TokenType.EOF
                ):
                    if self._current.value:
                        content_parts.append(" ")
                        content_parts.append(str(self._current.value))
                    self._advance()
                content_parts.append(" }}")
                if self._current.type == TokenType.VARIABLE_END:
                    self._advance()
            elif self._current.type == TokenType.BLOCK_END:
                content_parts.append("%}")
                self._advance()
            elif self._current.type == TokenType.COMMENT_BEGIN:
                content_parts.append("{#")
                self._advance()
            elif self._current.type == TokenType.COMMENT_END:
                content_parts.append(" #}")
                self._advance()
            else:
                # Include token value as literal
                if self._current.value:
                    content_parts.append(str(self._current.value))
                self._advance()

        return Raw(
            lineno=start.lineno,
            col_offset=start.col_offset,
            value="".join(content_parts),
        )

    def _parse_capture(self) -> Capture:
        """Parse {% capture name %}...{% end %} or {% endcapture %.

        Capture rendered content into a variable.

        Example:
            {% capture sidebar %}
                <nav>{{ build_nav() }}</nav>
            {% end %}

            {{ sidebar }}
        """
        start = self._advance()  # consume 'capture'
        self._push_block("capture", start)

        # Get variable name
        if self._current.type != TokenType.NAME:
            raise self._error(
                "Expected variable name",
                suggestion="Capture syntax: {% capture varname %}...{% end %}",
            )
        name = self._advance().value

        # Optional filter
        filter_node: Filter | None = None
        if self._match(TokenType.PIPE):
            self._advance()
            if self._current.type != TokenType.NAME:
                raise self._error("Expected filter name")
            filter_name = self._advance().value

            # Optional filter arguments
            filter_args: list[Expr] = []
            filter_kwargs: dict[str, Expr] = {}
            if self._match(TokenType.LPAREN):
                self._advance()
                filter_args, filter_kwargs = self._parse_call_args()
                self._expect(TokenType.RPAREN)

            # Create a placeholder Filter node (value will be the captured content)
            filter_node = Filter(
                lineno=start.lineno,
                col_offset=start.col_offset,
                value=Const(lineno=start.lineno, col_offset=start.col_offset, value=""),
                name=filter_name,
                args=tuple(filter_args),
                kwargs=filter_kwargs,
            )

        self._expect(TokenType.BLOCK_END)

        # Parse body using universal end detection
        body = self._parse_body()

        # Consume end tag
        self._consume_end_tag("capture")

        return Capture(
            lineno=start.lineno,
            col_offset=start.col_offset,
            name=name,
            body=tuple(body),
            filter=filter_node,
        )

    def _parse_cache(self) -> Cache:
        """Parse {% cache key %}...{% end %} or {% endcache %.

        Fragment caching with optional TTL.

        Example:
            {% cache "sidebar-" ~ site.nav_version %}
                {{ build_nav_tree(site.pages) }}
            {% end %}

            {% cache "weather", ttl="5m" %}
                {{ fetch_weather() }}
            {% end %}
        """
        start = self._advance()  # consume 'cache'
        self._push_block("cache", start)

        # Parse cache key expression
        key = self._parse_expression()

        # Optional TTL and depends
        ttl: Expr | None = None
        depends: list[Expr] = []

        while self._match(TokenType.COMMA):
            self._advance()
            if self._current.type == TokenType.NAME:
                if self._current.value == "ttl" and self._peek(1).type == TokenType.ASSIGN:
                    self._advance()  # consume 'ttl'
                    self._advance()  # consume '='
                    ttl = self._parse_expression()
                elif self._current.value == "depends" and self._peek(1).type == TokenType.ASSIGN:
                    self._advance()  # consume 'depends'
                    self._advance()  # consume '='
                    depends.append(self._parse_expression())
                else:
                    break
            else:
                break

        self._expect(TokenType.BLOCK_END)

        # Parse body using universal end detection
        body = self._parse_body()

        # Consume end tag
        self._consume_end_tag("cache")

        return Cache(
            lineno=start.lineno,
            col_offset=start.col_offset,
            key=key,
            body=tuple(body),
            ttl=ttl,
            depends=tuple(depends),
        )

    def _parse_filter_block(self) -> FilterBlock:
        """Parse {% filter name %}...{% end %} or {% endfilter %.

        Apply a filter to an entire block of content.

        Example:
            {% filter upper %}
                This will be UPPERCASE
            {% end %}
        """
        start = self._advance()  # consume 'filter'
        self._push_block("filter", start)

        # Get filter name
        if self._current.type != TokenType.NAME:
            raise self._error(
                "Expected filter name",
                suggestion="Filter block syntax: {% filter name %}...{% end %}",
            )
        filter_name = self._advance().value

        # Optional filter arguments
        filter_args: list[Expr] = []
        filter_kwargs: dict[str, Expr] = {}
        if self._match(TokenType.LPAREN):
            self._advance()
            filter_args, filter_kwargs = self._parse_call_args()
            self._expect(TokenType.RPAREN)

        self._expect(TokenType.BLOCK_END)

        # Parse body using universal end detection
        body = self._parse_body()

        # Consume end tag
        self._consume_end_tag("filter")

        # Create Filter node for the block
        filter_node = Filter(
            lineno=start.lineno,
            col_offset=start.col_offset,
            value=Const(lineno=start.lineno, col_offset=start.col_offset, value=""),
            name=filter_name,
            args=tuple(filter_args),
            kwargs=filter_kwargs,
        )

        return FilterBlock(
            lineno=start.lineno,
            col_offset=start.col_offset,
            filter=filter_node,
            body=tuple(body),
        )
