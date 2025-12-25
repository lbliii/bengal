"""JSON lexer for Rosettes.

Ultra-optimized hand-written scanner. No regex overhead.
Uses direct character scanning for maximum performance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rosettes._types import Token, TokenType
from rosettes.lexers._base import PatternLexer

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rosettes._config import LexerConfig

__all__ = ["JsonLexer"]

# Character sets for fast lookup
_WHITESPACE = frozenset(" \t\n\r")
_DIGITS = frozenset("0123456789")
_DIGITS_OR_SIGN = frozenset("0123456789+-")


class JsonLexer(PatternLexer):
    """JSON lexer — hand-optimized scanner.

    No regex overhead. Direct character scanning.
    Thread-safe: all state is local to method calls.
    """

    name = "json"
    aliases = ("json5",)
    filenames = ("*.json", "*.json5", "*.jsonc")
    mimetypes = ("application/json", "application/json5")

    # Not used - we override tokenize methods
    rules = ()

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
    ) -> Iterator[Token]:
        """Tokenize JSON with position tracking."""
        line = 1
        col = 1
        i = 0
        n = len(code)

        while i < n:
            c = code[i]

            # Whitespace
            if c in _WHITESPACE:
                start = i
                start_col = col
                start_line = line
                while i < n and code[i] in _WHITESPACE:
                    if code[i] == "\n":
                        line += 1
                        col = 1
                    else:
                        col += 1
                    i += 1
                yield Token(TokenType.WHITESPACE, code[start:i], start_line, start_col)
                continue

            # String
            if c == '"':
                start = i
                start_col = col
                i += 1
                col += 1
                while i < n:
                    c2 = code[i]
                    if c2 == "\\":
                        i += 2
                        col += 2
                    elif c2 == '"':
                        i += 1
                        col += 1
                        break
                    else:
                        i += 1
                        col += 1
                yield Token(TokenType.STRING, code[start:i], line, start_col)
                continue

            # Number
            if c in _DIGITS or (c == "-" and i + 1 < n and code[i + 1] in _DIGITS):
                start = i
                start_col = col
                if c == "-":
                    i += 1
                    col += 1
                # Integer part
                while i < n and code[i] in _DIGITS:
                    i += 1
                    col += 1
                # Fractional part
                if i < n and code[i] == ".":
                    i += 1
                    col += 1
                    while i < n and code[i] in _DIGITS:
                        i += 1
                        col += 1
                # Exponent
                if i < n and code[i] in "eE":
                    i += 1
                    col += 1
                    if i < n and code[i] in "+-":
                        i += 1
                        col += 1
                    while i < n and code[i] in _DIGITS:
                        i += 1
                        col += 1
                yield Token(TokenType.NUMBER, code[start:i], line, start_col)
                continue

            # Keywords: true, false, null
            if c == "t" and code[i : i + 4] == "true":
                yield Token(TokenType.KEYWORD_CONSTANT, "true", line, col)
                i += 4
                col += 4
                continue
            if c == "f" and code[i : i + 5] == "false":
                yield Token(TokenType.KEYWORD_CONSTANT, "false", line, col)
                i += 5
                col += 5
                continue
            if c == "n" and code[i : i + 4] == "null":
                yield Token(TokenType.KEYWORD_CONSTANT, "null", line, col)
                i += 4
                col += 4
                continue

            # Punctuation
            if c in "{}[]:,":
                yield Token(TokenType.PUNCTUATION, c, line, col)
                i += 1
                col += 1
                continue

            # Unknown character - skip
            i += 1
            col += 1

    def tokenize_fast(
        self,
        code: str,
    ) -> Iterator[tuple[TokenType, str]]:
        """Ultra-fast JSON tokenization. No position tracking."""
        i = 0
        n = len(code)
        WS = _WHITESPACE
        DIG = _DIGITS

        while i < n:
            c = code[i]

            # Whitespace - most common, check first
            if c in WS:
                start = i
                i += 1
                while i < n and code[i] in WS:
                    i += 1
                yield (TokenType.WHITESPACE, code[start:i])
                continue

            # String - second most common
            if c == '"':
                start = i
                i += 1
                while i < n:
                    c2 = code[i]
                    if c2 == "\\":
                        i += 2
                    elif c2 == '"':
                        i += 1
                        break
                    else:
                        i += 1
                yield (TokenType.STRING, code[start:i])
                continue

            # Punctuation - very common in JSON
            if c in "{}[]:,":
                yield (TokenType.PUNCTUATION, c)
                i += 1
                continue

            # Number
            if c in DIG or c == "-":
                start = i
                i += 1
                while i < n and code[i] in DIG:
                    i += 1
                if i < n and code[i] == ".":
                    i += 1
                    while i < n and code[i] in DIG:
                        i += 1
                if i < n and code[i] in "eE":
                    i += 1
                    if i < n and code[i] in "+-":
                        i += 1
                    while i < n and code[i] in DIG:
                        i += 1
                yield (TokenType.NUMBER, code[start:i])
                continue

            # Keywords
            if c == "t" and code[i : i + 4] == "true":
                yield (TokenType.KEYWORD_CONSTANT, "true")
                i += 4
                continue
            if c == "f" and code[i : i + 5] == "false":
                yield (TokenType.KEYWORD_CONSTANT, "false")
                i += 5
                continue
            if c == "n" and code[i : i + 4] == "null":
                yield (TokenType.KEYWORD_CONSTANT, "null")
                i += 4
                continue

            # Unknown - skip
            i += 1
