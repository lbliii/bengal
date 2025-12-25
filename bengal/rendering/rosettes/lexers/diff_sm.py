"""Hand-written Diff/Patch lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["DiffStateMachineLexer"]


class DiffStateMachineLexer(StateMachineLexer):
    """Diff/Patch lexer."""

    name = "diff"
    aliases = ("patch", "udiff")
    filenames = ("*.diff", "*.patch")
    mimetypes = ("text/x-diff", "text/x-patch")

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = 0

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Read entire line
            line_end = pos
            while line_end < length and code[line_end] != "\n":
                line_end += 1

            content = code[pos:line_end]

            # Determine line type
            token_type = TokenType.TEXT

            if content.startswith("+++") or content.startswith("---"):
                token_type = TokenType.GENERIC_HEADING
            elif content.startswith("@@"):
                token_type = TokenType.GENERIC_SUBHEADING
            elif content.startswith("+"):
                token_type = TokenType.GENERIC_INSERTED
            elif content.startswith("-"):
                token_type = TokenType.GENERIC_DELETED
            elif content.startswith("!"):
                token_type = TokenType.GENERIC_STRONG
            elif content.startswith("diff "):
                token_type = TokenType.GENERIC_HEADING
            elif content.startswith("index "):
                token_type = TokenType.COMMENT_SINGLE
            elif (
                content.startswith("Index: ")
                or content.startswith("===")
                or content.startswith("***")
            ):
                token_type = TokenType.GENERIC_HEADING
            elif content.startswith(" "):
                token_type = TokenType.TEXT

            yield Token(token_type, content, line, col)
            pos = line_end

            # Newline
            if pos < length and code[pos] == "\n":
                yield Token(TokenType.WHITESPACE, "\n", line, line_end - line_start + 1)
                pos += 1
                line += 1
                line_start = pos
