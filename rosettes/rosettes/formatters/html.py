"""HTML formatter for Rosettes.

Generates HTML output with Pygments-compatible CSS classes.
Thread-safe by design — no mutable shared state.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from rosettes._config import FormatConfig, HighlightConfig
from rosettes._escape import escape_html
from rosettes._types import Token, TokenType

__all__ = ["HtmlFormatter"]


@dataclass(frozen=True, slots=True)
class HtmlFormatter:
    """HTML formatter with streaming output.

    Thread-safe: all state is immutable or local to method calls.

    Attributes:
        config: Highlight configuration.
    """

    config: HighlightConfig = HighlightConfig()

    @property
    def name(self) -> str:
        """The canonical name of this formatter."""
        return "html"

    def format(
        self,
        tokens: Iterator[Token],
        config: FormatConfig | None = None,
    ) -> Iterator[str]:
        """Format tokens as HTML with streaming output.

        Args:
            tokens: Stream of tokens to format.
            config: Optional format configuration (overrides self.config).

        Yields:
            String chunks of HTML output.
        """
        if config is None:
            config = FormatConfig()

        css_class = config.css_class
        class_prefix = config.class_prefix

        # Opening tags
        if config.wrap_code:
            yield f'<div class="{css_class}">'
            yield "<pre>"
            # Optionally wrap in <code>
            yield "<code>"

        # Track current line for line highlighting
        current_line = 1
        hl_lines = self.config.hl_lines
        in_hl_line = current_line in hl_lines

        if in_hl_line:
            yield f'<span class="{self.config.hl_line_class}">'

        # Format each token
        for token in tokens:
            # Handle line changes
            while current_line < token.line:
                if in_hl_line:
                    yield "</span>"
                yield "\n"
                current_line += 1
                in_hl_line = current_line in hl_lines
                if in_hl_line:
                    yield f'<span class="{self.config.hl_line_class}">'

            # Format the token
            escaped_value = escape_html(token.value)

            if token.type == TokenType.TEXT or token.type == TokenType.WHITESPACE:
                # Plain text, no span
                yield escaped_value
            else:
                # Token with CSS class
                css_class_name = f"{class_prefix}{token.type.value}"
                yield f'<span class="{css_class_name}">{escaped_value}</span>'

            # Track newlines within the token value
            newlines = token.value.count("\n")
            if newlines:
                # Close highlight span before newlines
                if in_hl_line:
                    yield "</span>"

                for _ in range(newlines):
                    current_line += 1
                    in_hl_line = current_line in hl_lines

                # Re-open if needed
                if in_hl_line:
                    yield f'<span class="{self.config.hl_line_class}">'

        # Close any open highlight span
        if in_hl_line:
            yield "</span>"

        # Closing tags
        if config.wrap_code:
            yield "</code>"
            yield "</pre>"
            yield "</div>"

    def format_string(
        self,
        tokens: Iterator[Token],
        config: FormatConfig | None = None,
    ) -> str:
        """Format tokens as a single HTML string.

        Convenience method that joins format() output.

        Args:
            tokens: Stream of tokens to format.
            config: Optional format configuration.

        Returns:
            Complete HTML string.
        """
        return "".join(self.format(tokens, config))
