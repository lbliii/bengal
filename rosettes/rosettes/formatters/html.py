"""HTML formatter for Rosettes.

Generates HTML output with Pygments-compatible CSS classes.
Thread-safe by design — no mutable shared state.

Performance Optimizations:
    1. Fast path when no line highlighting needed
    2. Pre-computed escape table (C-level str.translate)
    3. Pre-built span templates (avoid f-string in loop)
    4. Direct token type value access (StrEnum)
    5. Streaming output (generator, no intermediate list)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

from rosettes._config import FormatConfig, HighlightConfig
from rosettes._escape import escape_html
from rosettes._types import Token, TokenType

__all__ = ["HtmlFormatter"]

# Pre-compute token types that don't need spans
_NO_SPAN_TYPES = frozenset({TokenType.TEXT, TokenType.WHITESPACE})

# Pre-build span templates for ALL token types (avoid f-string in hot path)
_SPAN_OPEN: dict[str, str] = {}
_SPAN_CLOSE = "</span>"
for _tt in TokenType:
    if _tt not in _NO_SPAN_TYPES:
        _SPAN_OPEN[_tt.value] = f'<span class="{_tt.value}">'


@dataclass(frozen=True, slots=True)
class HtmlFormatter:
    """HTML formatter with streaming output.

    Thread-safe: all state is immutable or local to method calls.
    """

    config: HighlightConfig = HighlightConfig()

    @property
    def name(self) -> str:
        return "html"

    def format_fast(
        self,
        tokens: Iterator[tuple[TokenType, str]],
        config: FormatConfig | None = None,
    ) -> Iterator[str]:
        """Ultra-fast formatting without line highlighting.

        Optimizations:
            - Pre-built span templates (no f-string per token)
            - Direct dict lookup (O(1))
            - Minimal branching in hot path
        """
        if config is None:
            config = FormatConfig()

        # Cache lookups
        no_span = _NO_SPAN_TYPES
        span_open = _SPAN_OPEN
        span_close = _SPAN_CLOSE
        escape = escape_html
        prefix = config.class_prefix

        # Use prefixed templates if needed
        if prefix:
            span_open = {k: f'<span class="{prefix}{k}">' for k in span_open}

        # Opening tags
        if config.wrap_code:
            yield f'<div class="{config.css_class}"><pre><code>'

        # Hot path - format each token
        for token_type, value in tokens:
            if token_type in no_span:
                yield escape(value)
            else:
                # Pre-built template: O(1) lookup + concatenation
                tv = token_type.value
                yield span_open[tv]
                yield escape(value)
                yield span_close

        # Closing tags
        if config.wrap_code:
            yield "</code></pre></div>"

    def format(
        self,
        tokens: Iterator[Token],
        config: FormatConfig | None = None,
    ) -> Iterator[str]:
        """Format tokens as HTML with streaming output."""
        if config is None:
            config = FormatConfig()

        hl_lines = self.config.hl_lines

        # Fast path: no line highlighting
        if not hl_lines:
            fast_tokens = ((t.type, t.value) for t in tokens)
            yield from self.format_fast(fast_tokens, config)
            return

        # Slow path: line highlighting
        no_span = _NO_SPAN_TYPES
        span_open = _SPAN_OPEN
        span_close = _SPAN_CLOSE
        escape = escape_html
        prefix = config.class_prefix
        hl_line_class = self.config.hl_line_class
        hl_span_open = f'<span class="{hl_line_class}">'

        if prefix:
            span_open = {k: f'<span class="{prefix}{k}">' for k in span_open}

        if config.wrap_code:
            yield f'<div class="{config.css_class}"><pre><code>'

        current_line = 1
        in_hl = current_line in hl_lines

        if in_hl:
            yield hl_span_open

        for token in tokens:
            # Handle line transitions
            while current_line < token.line:
                if in_hl:
                    yield span_close
                yield "\n"
                current_line += 1
                in_hl = current_line in hl_lines
                if in_hl:
                    yield hl_span_open

            # Format token
            escaped = escape(token.value)
            if token.type in no_span:
                yield escaped
            else:
                tv = token.type.value
                yield span_open[tv]
                yield escaped
                yield span_close

            # Track embedded newlines
            value = token.value
            nl_idx = value.find("\n")
            if nl_idx >= 0:
                if in_hl:
                    yield span_close
                # Count newlines without second scan
                newlines = value.count("\n", nl_idx)
                for _ in range(newlines):
                    current_line += 1
                    in_hl = current_line in hl_lines
                if in_hl:
                    yield hl_span_open

        if in_hl:
            yield span_close

        if config.wrap_code:
            yield "</code></pre></div>"

    def format_string(
        self,
        tokens: Iterator[Token],
        config: FormatConfig | None = None,
    ) -> str:
        return "".join(self.format(tokens, config))

    def format_string_fast(
        self,
        tokens: Iterator[tuple[TokenType, str]],
        config: FormatConfig | None = None,
    ) -> str:
        return "".join(self.format_fast(tokens, config))
