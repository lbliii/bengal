"""Hand-written Diff/Patch lexer optimized for speed.

O(n) guaranteed, zero regex, thread-safe.
Uses C-level str.find() for fast line scanning.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["DiffStateMachineLexer"]


class DiffStateMachineLexer(StateMachineLexer):
    """Diff/Patch lexer optimized with C-level str.find().

    Line-based format - uses find() to scan lines without allocating intermediate lists.
    """

    name = "diff"
    aliases = ("patch", "udiff")
    filenames = ("*.diff", "*.patch")
    mimetypes = ("text/x-diff", "text/x-patch")

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1

        while pos < length:
            # Use C-level find to get line end - much faster than char-by-char
            line_end = code.find("\n", pos)
            if line_end == -1:
                line_end = length
                has_newline = False
            else:
                has_newline = True

            content = code[pos:line_end]

            # Classify line by first character - most common cases first
            if content:
                first_char = content[0]

                if first_char == " ":
                    token_type = TokenType.TEXT
                elif first_char == "+":
                    token_type = (
                        TokenType.GENERIC_HEADING
                        if len(content) >= 3 and content[1:3] == "++"
                        else TokenType.GENERIC_INSERTED
                    )
                elif first_char == "-":
                    token_type = (
                        TokenType.GENERIC_HEADING
                        if len(content) >= 3 and content[1:3] == "--"
                        else TokenType.GENERIC_DELETED
                    )
                elif first_char == "@" and len(content) >= 2 and content[1] == "@":
                    token_type = TokenType.GENERIC_SUBHEADING
                elif first_char == "d" and content.startswith("diff "):
                    token_type = TokenType.GENERIC_HEADING
                elif first_char == "i" and content.startswith("index "):
                    token_type = TokenType.COMMENT_SINGLE
                elif (
                    first_char == "I"
                    and content.startswith("Index: ")
                    or first_char in "=*"
                    and len(content) >= 3
                    and content[:3] in ("===", "***")
                ):
                    token_type = TokenType.GENERIC_HEADING
                elif first_char == "!":
                    token_type = TokenType.GENERIC_STRONG
                else:
                    token_type = TokenType.TEXT

                yield Token(token_type, content, line, 1)

            pos = line_end

            # Handle newline
            if has_newline:
                col = len(content) + 1 if content else 1
                yield Token(TokenType.WHITESPACE, "\n", line, col)
                pos += 1
                line += 1
