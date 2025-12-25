"""Hand-written JSON lexer using composable scanner mixins.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["JsonStateMachineLexer"]


_CONSTANTS: frozenset[str] = frozenset({"true", "false", "null"})


class JsonStateMachineLexer(StateMachineLexer):
    """JSON lexer. Simple, no comments, no special features."""

    name = "json"
    aliases = ()
    filenames = ("*.json",)
    mimetypes = ("application/json",)

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = 0

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Whitespace
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

            # Strings (keys and values)
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS or char == "-":
                start = pos
                if char == "-":
                    pos += 1
                # Integer part
                while pos < length and code[pos] in DIGITS:
                    pos += 1
                # Fractional part
                if pos < length and code[pos] == ".":
                    pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                # Exponent
                if pos < length and code[pos] in "eE":
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                value = code[start:pos]
                token_type = (
                    TokenType.NUMBER_FLOAT
                    if "." in value or "e" in value.lower()
                    else TokenType.NUMBER_INTEGER
                )
                yield Token(token_type, value, line, col)
                continue

            # Constants (true, false, null)
            if char in "tfn":
                for const in _CONSTANTS:
                    if code[pos : pos + len(const)] == const:
                        yield Token(TokenType.KEYWORD_CONSTANT, const, line, col)
                        pos += len(const)
                        break
                else:
                    yield Token(TokenType.ERROR, char, line, col)
                    pos += 1
                continue

            # Punctuation
            if char in "[]{},:":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1
