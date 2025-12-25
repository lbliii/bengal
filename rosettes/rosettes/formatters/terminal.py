"""Terminal formatter for Rosettes.

Generates ANSI-colored output for terminal display.
Thread-safe by design — no mutable shared state.

Supports three color modes:
    - 16: Standard 16 ANSI colors (most compatible)
    - 256: Extended 256-color palette
    - truecolor: 24-bit RGB colors
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rosettes.themes._mapping import ROLE_MAPPING
from rosettes.themes._roles import SyntaxRole

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Literal

    from rosettes._types import Token, TokenType
    from rosettes.themes._terminal import TerminalPalette

    ColorMode = Literal["16", "256", "truecolor"]

__all__ = ["TerminalFormatter"]


# ANSI escape sequences
ANSI_RESET = "\033[0m"
ANSI_ESCAPE = "\033["


# Map SyntaxRole to attribute name on TerminalPalette
ROLE_TO_ATTR: dict[SyntaxRole, str] = {
    SyntaxRole.CONTROL_FLOW: "control_flow",
    SyntaxRole.DECLARATION: "declaration",
    SyntaxRole.IMPORT: "import_",
    SyntaxRole.STRING: "string",
    SyntaxRole.DOCSTRING: "docstring",
    SyntaxRole.NUMBER: "number",
    SyntaxRole.BOOLEAN: "boolean",
    SyntaxRole.TYPE: "type_",
    SyntaxRole.FUNCTION: "function",
    SyntaxRole.VARIABLE: "variable",
    SyntaxRole.CONSTANT: "constant",
    SyntaxRole.COMMENT: "comment",
    SyntaxRole.ERROR: "error",
    SyntaxRole.WARNING: "warning",
    SyntaxRole.ADDED: "added",
    SyntaxRole.REMOVED: "removed",
    SyntaxRole.TEXT: "text",
    SyntaxRole.MUTED: "muted",
    SyntaxRole.PUNCTUATION: "punctuation",
    SyntaxRole.OPERATOR: "operator",
    SyntaxRole.ATTRIBUTE: "attribute",
    SyntaxRole.NAMESPACE: "namespace",
    SyntaxRole.TAG: "tag",
    SyntaxRole.REGEX: "string",  # Fallback
    SyntaxRole.ESCAPE: "escape",
}


@dataclass(frozen=True, slots=True)
class TerminalFormatter:
    """Terminal formatter with ANSI color output.

    Thread-safe: all state is immutable.

    Attributes:
        palette: The terminal palette to use for colors.
        color_mode: Color mode ("16", "256", or "truecolor").
        reset_at_newline: If True, reset colors at each newline.
    """

    palette: TerminalPalette | None = None
    color_mode: ColorMode = "256"
    reset_at_newline: bool = True

    @property
    def name(self) -> str:
        return "terminal"

    def _get_palette(self) -> TerminalPalette:
        """Get the palette, creating a default if needed."""
        if self.palette is not None:
            return self.palette

        # Import here to avoid circular dependency
        from rosettes.themes.palettes.monokai import TERMINAL_MONOKAI

        return TERMINAL_MONOKAI

    def format(self, tokens: Iterator[Token]) -> Iterator[str]:
        """Format tokens as ANSI-colored text.

        Args:
            tokens: Iterator of tokens to format.

        Yields:
            Strings with ANSI escape codes.
        """
        palette = self._get_palette()

        for token in tokens:
            role = ROLE_MAPPING.get(token.type, SyntaxRole.TEXT)
            attr_name = ROLE_TO_ATTR.get(role, "text")
            ansi_code = getattr(palette, attr_name, "0")

            value = token.value

            # Handle newlines with reset if configured
            if self.reset_at_newline and "\n" in value:
                parts = value.split("\n")
                for i, part in enumerate(parts):
                    if part:
                        if ansi_code and ansi_code != "0":
                            yield f"{ANSI_ESCAPE}{ansi_code}m{part}{ANSI_RESET}"
                        else:
                            yield part
                    if i < len(parts) - 1:
                        yield "\n"
            else:
                if ansi_code and ansi_code != "0":
                    yield f"{ANSI_ESCAPE}{ansi_code}m{value}{ANSI_RESET}"
                else:
                    yield value

    def format_fast(
        self,
        tokens: Iterator[tuple[TokenType, str]],
    ) -> Iterator[str]:
        """Ultra-fast formatting without line tracking.

        Args:
            tokens: Iterator of (token_type, value) tuples.

        Yields:
            Strings with ANSI escape codes.
        """
        palette = self._get_palette()

        for token_type, value in tokens:
            role = ROLE_MAPPING.get(token_type, SyntaxRole.TEXT)
            attr_name = ROLE_TO_ATTR.get(role, "text")
            ansi_code = getattr(palette, attr_name, "0")

            if ansi_code and ansi_code != "0":
                yield f"{ANSI_ESCAPE}{ansi_code}m{value}{ANSI_RESET}"
            else:
                yield value

    def format_string(self, tokens: Iterator[Token]) -> str:
        """Format tokens and return as a single string.

        Args:
            tokens: Iterator of tokens to format.

        Returns:
            ANSI-colored string.
        """
        return "".join(self.format(tokens))

    def format_string_fast(
        self,
        tokens: Iterator[tuple[TokenType, str]],
    ) -> str:
        """Fast format tokens and return as a single string.

        Args:
            tokens: Iterator of (token_type, value) tuples.

        Returns:
            ANSI-colored string.
        """
        return "".join(self.format_fast(tokens))
