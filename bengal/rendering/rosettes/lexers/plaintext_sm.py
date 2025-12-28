"""Plaintext lexer for code blocks without syntax highlighting.

O(n) guaranteed, zero regex, thread-safe.
Simply emits the content as TEXT tokens without any highlighting.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["PlaintextStateMachineLexer"]


class PlaintextStateMachineLexer(StateMachineLexer):
    """Plaintext lexer - no syntax highlighting, just renders as plain text."""

    name = "plaintext"
    aliases = ("text", "plain", "txt", "none", "raw")
    filenames = ("*.txt",)
    mimetypes = ("text/plain",)

    WHITESPACE = frozenset(" \t\n\r")

    def tokenize(self, code: str) -> Iterator[Token]:
        """Tokenize plaintext by splitting into whitespace and text chunks.

        Args:
            code: The source code to tokenize.

        Yields:
            Token objects for WHITESPACE and TEXT.
        """
        pos = 0
        length = len(code)
        line = 1
        line_start = start

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Whitespace (preserve newlines for line tracking)
            if char in self.WHITESPACE:
                start = pos
                start_line = line
                while pos < length and code[pos] in self.WHITESPACE:
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start:pos], start_line, col)
                continue

            # Non-whitespace text
            start = pos
            while pos < length and code[pos] not in self.WHITESPACE:
                pos += 1
            yield Token(TokenType.TEXT, code[start:pos], line, col)
