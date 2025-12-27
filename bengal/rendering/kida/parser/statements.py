"""Statement parsing for Kida parser.

Provides mixin for parsing template statements (body, data, output, blocks).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.kida._types import TokenType
from bengal.rendering.kida.nodes import Data, Output

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Expr, Node


class StatementParsingMixin:
    """Mixin for parsing template statements.

    Required Host Attributes:
        - All from TokenNavigationMixin
        - All from BlockParsingMixin
        - _END_KEYWORDS: frozenset[str]
        - _CONTINUATION_KEYWORDS: frozenset[str]
        - _parse_block: method
        - _parse_block_content: method
        - _parse_expression: method
    """

    def _parse_body(self, stop_on_continuation: bool = False) -> list[Node]:
        """Parse template body until an end tag or EOF.

        Uses universal end detection: stops on ANY end keyword (end, endif,
        endfor, enddef, etc.) or continuation keyword (else, elif, empty)
        if stop_on_continuation is True.

        This enables the unified {% end %} syntax where {% end %} always
        closes the innermost open block.

        Args:
            stop_on_continuation: If True, also stop on else/elif/empty keywords.
                                 Used by if/for blocks that have continuation clauses.

        Returns:
            List of parsed nodes.
        """
        nodes: list[Node] = []

        while self._current.type != TokenType.EOF:
            # Check for block begin that might contain end/continuation keyword
            if self._current.type == TokenType.BLOCK_BEGIN:
                # Peek ahead to see if next token is an end or continuation keyword
                next_tok = self._peek(1)
                if next_tok.type == TokenType.NAME:
                    # Stop on ANY end keyword - this is the key to unified {% end %}
                    if next_tok.value in self._END_KEYWORDS:
                        # Don't consume the BLOCK_BEGIN, let parent handle closing
                        break

                    # Stop on continuation keywords if requested (for if/for blocks)
                    if stop_on_continuation and next_tok.value in self._CONTINUATION_KEYWORDS:
                        break

                result = self._parse_block()
                if result is not None:
                    # Flatten multi-set results (returns list[Node])
                    if isinstance(result, list):
                        nodes.extend(result)
                    else:
                        nodes.append(result)
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
            escape=self._autoescape,
        )

    def _parse_block(self) -> Node | list[Node] | None:
        """Parse {% ... %} block tag.

        Returns:
            - Single Node for most blocks
            - list[Node] for multi-set ({% set a = 1, b = 2 %})
            - None for end tags
        """
        self._expect(TokenType.BLOCK_BEGIN)
        return self._parse_block_content()

    def _parse_block_content(self) -> Node | list[Node] | None:
        """Parse block content after BLOCK_BEGIN is consumed.

        This is split from _parse_block so it can be reused in contexts
        where BLOCK_BEGIN is already consumed (e.g., inside macro bodies).

        Returns:
            - Single Node for most blocks
            - list[Node] for multi-set ({% set a = 1, b = 2 %})
            - None for end tags
        """
        if self._current.type != TokenType.NAME:
            raise self._error(
                "Expected block keyword (if, for, set, block, etc.)",
                suggestion="Block tags should start with a keyword like {% if %}, {% for %}, {% set %}",
            )

        keyword = self._current.value

        if keyword == "if":
            return self._parse_if()
        elif keyword == "unless":
            # RFC: kida-modern-syntax-features
            return self._parse_unless()
        elif keyword == "for":
            return self._parse_for()
        elif keyword == "break":
            # RFC: kida-modern-syntax-features
            return self._parse_break()
        elif keyword == "continue":
            # RFC: kida-modern-syntax-features
            return self._parse_continue()
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
        elif keyword == "do":
            return self._parse_do()
        elif keyword == "raw":
            return self._parse_raw()
        elif keyword == "def":
            return self._parse_def()
        elif keyword == "call":
            return self._parse_call()
        elif keyword == "capture":
            return self._parse_capture()
        elif keyword == "cache":
            return self._parse_cache()
        elif keyword == "filter":
            return self._parse_filter_block()
        elif keyword == "slot":
            return self._parse_slot()
        elif keyword == "match":
            return self._parse_match()
        elif keyword == "spaceless":
            # RFC: kida-modern-syntax-features
            return self._parse_spaceless()
        elif keyword == "embed":
            # RFC: kida-modern-syntax-features
            return self._parse_embed()
        elif keyword in ("elif", "else", "empty", "case"):
            # Continuation tags outside of their block context
            raise self._error(
                f"Unexpected '{keyword}' - not inside a matching block",
                suggestion=f"'{keyword}' can only appear inside an 'if' or 'for' block",
            )
        elif keyword in (
            "endif",
            "endfor",
            "endblock",
            "endmacro",
            "endwith",
            "endraw",
            "end",
            "enddef",
            "endcall",
            "endcapture",
            "endcache",
            "endfilter",
            "endmatch",
            "endspaceless",
            "endembed",
        ):
            # End tags without matching opening block
            if not self._block_stack:
                raise self._error(
                    f"Unexpected '{keyword}' - no open block to close",
                    suggestion="Remove this tag or add a matching opening tag",
                )
            # If we have open blocks, this is likely a mismatch
            # Check if it matches the innermost block
            innermost_block = self._block_stack[-1][0]
            expected_end = f"end{innermost_block}" if innermost_block != "block" else "endblock"
            if keyword == "end":
                # Unified {% end %} is always valid if there's an open block
                return None
            elif keyword == expected_end:
                # Matching end tag - let parent handle it
                return None
            else:
                # Mismatched end tag
                raise self._error(
                    f"Mismatched closing tag: expected '{{% {expected_end} %}}' or '{{% end %}}', got '{{% {keyword} %}}'",
                    suggestion=f"The innermost open block is '{innermost_block}' (opened at line {self._block_stack[-1][1]})",
                )
        else:
            raise self._error(
                f"Unknown block keyword: {keyword}",
                suggestion="Valid keywords: if, unless, for, break, continue, set, let, block, extends, include, macro, from, with, do, raw, def, call, capture, cache, filter, slot, match, spaceless, embed",
            )

    def _skip_comment(self) -> None:
        """Skip comment block."""
        self._expect(TokenType.COMMENT_BEGIN)
        self._expect(TokenType.COMMENT_END)

    def _get_eof_error_suggestion(self, block_type: str) -> str:
        """Generate improved error suggestion for EOF errors in blocks.

        Checks for unclosed comments and provides helpful suggestions.
        """
        unclosed = self._check_unclosed_comment()
        if unclosed:
            unclosed_line, unclosed_col = unclosed
            return (
                f"Unclosed comment at line {unclosed_line}:{unclosed_col}. "
                f"Add '#}}' to close the comment, "
                f"or add {{% end %}} to close the {block_type} block."
            )
        return f"Add {{% end %}} or {{% end{block_type} %}}"

    def _check_unclosed_comment(self) -> tuple[int, int] | None:
        """Check for unclosed comment in the source.

        Scans the source for {# without matching #}.
        Returns (line, col) of unclosed comment start if found, None otherwise.
        """
        if not self._source:
            return None

        lines = self._source.splitlines()

        comment_start_line = None
        comment_start_col = None
        in_comment = False

        for line_num, line in enumerate(lines, 1):
            pos = 0

            while pos < len(line):
                if not in_comment:
                    # Look for comment start
                    start_pos = line.find("{#", pos)
                    if start_pos == -1:
                        break
                    # Check if comment closes on same line
                    end_pos = line.find("#}", start_pos + 2)
                    if end_pos == -1:
                        # Comment starts but doesn't close - track it
                        in_comment = True
                        comment_start_line = line_num
                        comment_start_col = start_pos
                        pos = start_pos + 2
                    else:
                        # Comment closed on same line, skip past it
                        pos = end_pos + 2
                else:
                    # Inside comment, look for closing
                    end_pos = line.find("#}", pos)
                    if end_pos == -1:
                        # Comment continues to next line
                        break
                    # Comment closes here
                    in_comment = False
                    pos = end_pos + 2

        if in_comment and comment_start_line is not None:
            return (comment_start_line, comment_start_col or 0)

        return None

    # Helper methods for tuple/assignment parsing
    def _parse_tuple_or_name(self) -> Expr:
        """Parse assignment target (variable or tuple for unpacking).

        Used by set/let/export for patterns like:
            - x (single variable)
            - a, b (comma-separated before '=')
            - (a, b) (parenthesized tuple)
        """
        from bengal.rendering.kida.nodes import Tuple

        # Check for parenthesized tuple
        if self._match(TokenType.LPAREN):
            return self._parse_primary()  # Will parse as tuple

        # Parse first name
        first = self._parse_primary()

        # Check for comma (tuple unpacking without parens)
        if self._match(TokenType.COMMA):
            items = [first]
            while self._match(TokenType.COMMA):
                self._advance()
                if self._current.type == TokenType.ASSIGN:
                    break  # trailing comma before '='
                items.append(self._parse_primary())

            return Tuple(
                lineno=first.lineno,
                col_offset=first.col_offset,
                items=tuple(items),
                ctx="store",
            )

        return first

    def _parse_tuple_or_expression(self) -> Expr:
        """Parse expression that may be an implicit tuple.

        Used for value side of set statements like:
            {% set a, b = 1, 2 %}

        The value `1, 2` is parsed as a tuple without parentheses.
        """
        from bengal.rendering.kida.nodes import Tuple

        first = self._parse_expression()

        # Check for comma (implicit tuple like 1, 2, 3)
        if self._match(TokenType.COMMA):
            items = [first]
            while self._match(TokenType.COMMA):
                self._advance()
                if self._match(TokenType.BLOCK_END):
                    break  # trailing comma before %}
                items.append(self._parse_expression())

            return Tuple(
                lineno=first.lineno,
                col_offset=first.col_offset,
                items=tuple(items),
                ctx="load",
            )

        return first

    def _parse_for_target(self) -> Expr:
        """Parse for loop target (variable or tuple for unpacking).

        Handles:
            - item (single variable)
            - (a, b) (parenthesized tuple)
            - a, b, c (comma-separated names before 'in')
        """
        from bengal.rendering.kida.nodes import Tuple

        # Check for parenthesized tuple
        if self._match(TokenType.LPAREN):
            return self._parse_primary()  # Will parse as tuple

        # Parse first name
        first = self._parse_primary()

        # Check for comma (tuple unpacking without parens)
        if self._match(TokenType.COMMA):
            items = [first]
            while self._match(TokenType.COMMA):
                self._advance()
                if self._current.type == TokenType.IN:
                    break  # trailing comma before 'in'
                items.append(self._parse_primary())

            return Tuple(
                lineno=first.lineno,
                col_offset=first.col_offset,
                items=tuple(items),
                ctx="store",
            )

        return first
