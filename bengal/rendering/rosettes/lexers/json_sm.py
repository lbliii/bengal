"""Hand-written JSON lexer optimized for speed.

O(n) guaranteed, zero regex; uses frozenset for O(1) character lookups, thread-safe.
Minimal overhead for the simple JSON grammar.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["JsonStateMachineLexer"]


# Pre-computed for fast lookup
_DIGITS = frozenset("0123456789")


class JsonStateMachineLexer(StateMachineLexer):
    """JSON lexer optimized for minimal overhead.

    JSON has a simple grammar - optimize for the common case.
    """

    name = "json"
    aliases = ()
    filenames = ("*.json",)
    mimetypes = ("application/json",)

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> Iterator[Token]:
        pos = start
        length = end if end is not None else len(code)
        line = 1
        line_start = starttart

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Whitespace - inline for speed
            if char in " \t\n\r":
                start = pos
                start_line = line
                while pos < length and code[pos] in " \t\n\r":
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start:pos], start_line, col)
                continue

            # Strings - simple inline scanning (JSON strings can't span lines)
            if char == '"':
                start = pos
                pos += 1
                while pos < length:
                    c = code[pos]
                    if c == '"':
                        pos += 1
                        break
                    if c == "\\":
                        pos += 2  # Skip escape sequence
                    else:
                        pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Numbers - inline for speed
            if char in _DIGITS or char == "-":
                start = pos
                if char == "-":
                    pos += 1
                # Integer part
                while pos < length and code[pos] in _DIGITS:
                    pos += 1
                # Fractional part
                is_float = False
                if pos < length and code[pos] == ".":
                    is_float = True
                    pos += 1
                    while pos < length and code[pos] in _DIGITS:
                        pos += 1
                # Exponent
                if pos < length and code[pos] in "eE":
                    is_float = True
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and code[pos] in _DIGITS:
                        pos += 1
                token_type = TokenType.NUMBER_FLOAT if is_float else TokenType.NUMBER_INTEGER
                yield Token(token_type, code[start:pos], line, col)
                continue

            # Constants - direct comparison (faster than loop)
            if char == "t" and code[pos : pos + 4] == "true":
                yield Token(TokenType.KEYWORD_CONSTANT, "true", line, col)
                pos += 4
                continue
            if char == "f" and code[pos : pos + 5] == "false":
                yield Token(TokenType.KEYWORD_CONSTANT, "false", line, col)
                pos += 5
                continue
            if char == "n" and code[pos : pos + 4] == "null":
                yield Token(TokenType.KEYWORD_CONSTANT, "null", line, col)
                pos += 4
                continue

            # Punctuation
            if char in "[]{},:":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1
