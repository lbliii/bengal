"""Parser error handling for Kida.

Provides ParseError class with rich source context and suggestions.
"""

from __future__ import annotations

from bengal.rendering.kida._types import Token


class ParseError(Exception):
    """Parser error with rich source context.

    Displays errors with source code snippets and visual pointers,
    matching the format used by the lexer for consistency.
    """

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
        """Format error with source context like Rust/modern compilers."""
        # Header with location
        location = self.filename or "<template>"
        header = f"Parse Error: {self.message}\n  --> {location}:{self.token.lineno}:{self.token.col_offset}"

        # Source context (if available)
        if self.source:
            lines = self.source.splitlines()
            if 0 < self.token.lineno <= len(lines):
                error_line = lines[self.token.lineno - 1]
                # Create pointer to error location
                pointer = " " * self.token.col_offset + "^"

                # Build the error display
                line_num = self.token.lineno
                msg = f"""
{header}
   |
{line_num:>3} | {error_line}
   | {pointer}"""
            else:
                msg = f"\n{header}"
        else:
            # Fallback without source
            msg = f"\n{header}"

        # Add suggestion if available
        if self.suggestion:
            msg += f"\n\nSuggestion: {self.suggestion}"

        return msg
