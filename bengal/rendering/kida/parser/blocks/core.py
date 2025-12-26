"""Core block stack management for Kida parser.

Provides base mixin for managing block stack and unified {% end %} syntax.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.rendering.kida._types import Token, TokenType

if TYPE_CHECKING:
    pass


class BlockStackMixin:
    """Mixin for block stack management.

    Required Host Attributes:
        - _block_stack: list[tuple[str, int, int]]
        - _current: Token (from TokenNavigationMixin)
        - _error: method (from TokenNavigationMixin)
        - _get_eof_error_suggestion: method
        - _expect: method (from TokenNavigationMixin)
        - _advance: method (from TokenNavigationMixin)
    """

    # All keywords that close blocks - used for universal end detection
    _END_KEYWORDS: frozenset[str] = frozenset(
        {
            "end",
            "endif",
            "endfor",
            "endblock",
            "endmacro",
            "endwith",
            "enddef",
            "endcall",
            "endcapture",
            "endcache",
            "endfilter",
            "endraw",
            "endmatch",
            "endspaceless",
            "endembed",
            "endunless",  # RFC: kida-modern-syntax-features
        }
    )

    # Keywords that continue a block (don't close it, but stop body parsing)
    _CONTINUATION_KEYWORDS: frozenset[str] = frozenset(
        {
            "else",
            "elif",
            "empty",
            "case",
        }
    )

    # Block types that are loops (for break/continue validation)
    _LOOP_BLOCKS: frozenset[str] = frozenset({"for", "while"})

    def _push_block(self, block_type: str, token: Token | None = None) -> None:
        """Push a block onto the stack when opening it.

        Args:
            block_type: Type of block (if, for, def, macro, etc.)
            token: Token for error reporting (defaults to current token)
        """
        tok = token or self._current
        self._block_stack.append((block_type, tok.lineno, tok.col_offset))

    def _pop_block(self, expected: str | None = None) -> str:
        """Pop a block from the stack when closing it.

        Args:
            expected: If provided, validates that the closing block matches.
                     Use None to accept any block type (unified {% end %}).

        Returns:
            The block type that was popped.

        Raises:
            ParseError: If no blocks are open or if expected doesn't match.
        """
        if not self._block_stack:
            raise self._error(
                "Unexpected closing tag - no open block to close",
                suggestion="Remove this tag or add a matching opening tag",
            )

        block_type, lineno, col = self._block_stack.pop()

        # If a specific block type is expected, validate it
        if expected and block_type != expected:
            raise self._error(
                f"Mismatched closing tag: expected {{% end{expected} %}}, "
                f"but found closing tag for '{block_type}' block opened at line {lineno}",
                suggestion=f"Use {{% end %}} to close the innermost block, "
                f"or {{% end{block_type} %}} to be explicit",
            )

        return block_type

    def _format_open_blocks(self) -> str:
        """Format the current block stack for error messages."""
        if not self._block_stack:
            return "No open blocks"
        blocks = []
        for block_type, lineno, _col in reversed(self._block_stack):
            blocks.append(f"  - {block_type} (opened at line {lineno})")
        return "Open blocks:\n" + "\n".join(blocks)

    def _in_loop(self) -> bool:
        """Check if currently inside a loop block.

        Used by break/continue to validate they are inside a loop.
        Part of RFC: kida-modern-syntax-features.
        """
        return any(block_type in self._LOOP_BLOCKS for block_type, _, _ in self._block_stack)

    def _consume_end_tag(self, block_type: str) -> None:
        """Consume an end tag ({% end %} or {% endXXX %}) and pop from stack.

        Args:
            block_type: The expected block type being closed.

        This method handles both unified {% end %} and explicit {% endif %} etc.
        """
        # Handle EOF - template ended without closing tag
        if self._current.type == TokenType.EOF:
            # Check for unclosed comments that might have caused the issue
            suggestion = self._get_eof_error_suggestion(block_type)
            raise self._error(
                f"Unexpected end of template - unclosed {block_type} block",
                suggestion=suggestion,
            )

        if self._current.type != TokenType.BLOCK_BEGIN:
            raise self._error(
                f"Expected closing tag for {block_type} block",
                suggestion=f"Add {{% end %}} or {{% end{block_type} %}}",
            )

        self._advance()  # consume {%

        if self._current.type != TokenType.NAME:
            raise self._error(f"Expected 'end' or 'end{block_type}'")

        keyword = self._current.value

        # Accept unified {% end %} or specific {% endXXX %}
        if keyword == "end":
            self._advance()  # consume 'end'
            self._pop_block()  # Pop without type checking - unified end
        elif keyword == f"end{block_type}":
            self._advance()  # consume 'endXXX'
            self._pop_block(block_type)  # Pop with type validation
        else:
            raise self._error(
                f"Expected 'end' or 'end{block_type}', got '{keyword}'",
                suggestion="Use {% end %} to close the innermost block",
            )

        self._expect(TokenType.BLOCK_END)
