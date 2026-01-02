"""Hand-written CSV lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._config import LexerConfig
from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import DIGITS
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["CsvStateMachineLexer"]


class CsvStateMachineLexer(StateMachineLexer):
    """CSV file lexer.

    Highlights:
    - Quoted strings (including escaped quotes)
    - Numbers (integers and floats)
    - Delimiters (comma, semicolon, tab)
    - Whitespace
    """

    name = "csv"
    aliases = ("tsv",)
    filenames = ("*.csv", "*.tsv")
    mimetypes = ("text/csv", "text/tab-separated-values")

    # Common CSV delimiters
    DELIMITERS = frozenset(",;\t")

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
        line_start = start

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Whitespace (space only, not delimiters)
            if char == " ":
                start_pos = pos
                while pos < length and code[pos] == " ":
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start_pos:pos], line, col)
                continue

            # Newline
            if char == "\n":
                yield Token(TokenType.WHITESPACE, char, line, col)
                pos += 1
                line += 1
                line_start = pos
                continue

            # Carriage return (handle \r\n and standalone \r)
            if char == "\r":
                if pos + 1 < length and code[pos + 1] == "\n":
                    yield Token(TokenType.WHITESPACE, "\r\n", line, col)
                    pos += 2
                else:
                    yield Token(TokenType.WHITESPACE, char, line, col)
                    pos += 1
                line += 1
                line_start = pos
                continue

            # Delimiters (comma, semicolon, tab)
            if char in self.DELIMITERS:
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            # Quoted strings (double quotes)
            if char == '"':
                start_pos = pos
                pos += 1
                while pos < length:
                    if code[pos] == '"':
                        # Check for escaped quote ("")
                        if pos + 1 < length and code[pos + 1] == '"':
                            pos += 2
                            continue
                        # End of string
                        pos += 1
                        break
                    elif code[pos] == "\n":
                        # Track line numbers within multi-line strings
                        line += 1
                        line_start = pos + 1
                        pos += 1
                    else:
                        pos += 1
                yield Token(TokenType.STRING, code[start_pos:pos], line, col)
                continue

            # Single-quoted strings
            if char == "'":
                start_pos = pos
                pos += 1
                while pos < length:
                    if code[pos] == "'":
                        # Check for escaped quote ('')
                        if pos + 1 < length and code[pos + 1] == "'":
                            pos += 2
                            continue
                        pos += 1
                        break
                    elif code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                        pos += 1
                    else:
                        pos += 1
                yield Token(TokenType.STRING, code[start_pos:pos], line, col)
                continue

            # Numbers (including negative and floats)
            if (
                char in DIGITS
                or (char == "-" and pos + 1 < length and code[pos + 1] in DIGITS)
                or (char == "+" and pos + 1 < length and code[pos + 1] in DIGITS)
            ):
                start_pos = pos
                if char in "+-":
                    pos += 1
                # Integer part
                while pos < length and code[pos] in DIGITS:
                    pos += 1
                is_float = False
                # Decimal part
                if pos < length and code[pos] == ".":
                    next_pos = pos + 1
                    if next_pos < length and code[next_pos] in DIGITS:
                        is_float = True
                        pos += 1
                        while pos < length and code[pos] in DIGITS:
                            pos += 1
                # Exponent part (e.g., 1e10, 1E-5)
                if pos < length and code[pos] in "eE":
                    next_pos = pos + 1
                    if next_pos < length and (code[next_pos] in DIGITS or code[next_pos] in "+-"):
                        is_float = True
                        pos += 1
                        if pos < length and code[pos] in "+-":
                            pos += 1
                        while pos < length and code[pos] in DIGITS:
                            pos += 1
                token_type = TokenType.NUMBER_FLOAT if is_float else TokenType.NUMBER_INTEGER
                yield Token(token_type, code[start_pos:pos], line, col)
                continue

            # Unquoted field value (text until delimiter or newline)
            start_pos = pos
            while pos < length and code[pos] not in self.DELIMITERS and code[pos] not in "\n\r":
                pos += 1
            if pos > start_pos:
                yield Token(TokenType.TEXT, code[start_pos:pos], line, col)
                continue

            # Fallback: single character
            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
