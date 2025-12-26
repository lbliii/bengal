"""Hand-written Diff/Patch lexer using line-oriented approach.

O(n) guaranteed, zero regex, thread-safe.
Uses C-level splitlines() for maximum performance.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["DiffStateMachineLexer"]


class DiffStateMachineLexer(StateMachineLexer):
    """Diff/Patch lexer using line-oriented processing.

    Uses C-level splitlines() instead of character-by-character scanning.
    """

    name = "diff"
    aliases = ("patch", "udiff")
    filenames = ("*.diff", "*.patch")
    mimetypes = ("text/x-diff", "text/x-patch")

    def tokenize(self, code: str) -> Iterator[Token]:
        # Use C-level splitlines() for fast line extraction
        line_num = 1

        for line_content in code.splitlines(keepends=True):
            # Strip newline for classification, keep for output
            has_newline = line_content.endswith("\n")
            content = line_content.rstrip("\n\r")

            # Classify line by first character(s) - ordered by frequency
            if content:
                first_char = content[0]

                if first_char == "+":
                    if content.startswith("+++"):
                        token_type = TokenType.GENERIC_HEADING
                    else:
                        token_type = TokenType.GENERIC_INSERTED
                elif first_char == "-":
                    if content.startswith("---"):
                        token_type = TokenType.GENERIC_HEADING
                    else:
                        token_type = TokenType.GENERIC_DELETED
                elif first_char == "@" and content.startswith("@@"):
                    token_type = TokenType.GENERIC_SUBHEADING
                elif first_char == " ":
                    token_type = TokenType.TEXT
                elif first_char == "d" and content.startswith("diff "):
                    token_type = TokenType.GENERIC_HEADING
                elif first_char == "i" and content.startswith("index "):
                    token_type = TokenType.COMMENT_SINGLE
                elif (
                    first_char == "I"
                    and content.startswith("Index: ")
                    or first_char == "="
                    and content.startswith("===")
                    or first_char == "*"
                    and content.startswith("***")
                ):
                    token_type = TokenType.GENERIC_HEADING
                elif first_char == "!":
                    token_type = TokenType.GENERIC_STRONG
                else:
                    token_type = TokenType.TEXT

                yield Token(token_type, content, line_num, 1)

            # Emit newline as separate whitespace token
            if has_newline:
                col = len(content) + 1 if content else 1
                yield Token(TokenType.WHITESPACE, "\n", line_num, col)
                line_num += 1
            elif not content:
                # Empty line without newline (shouldn't happen often)
                pass
