"""Hand-written TOML lexer using composable scanner mixins.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._config import LexerConfig
from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    BINARY_DIGITS,
    DIGITS,
    HEX_DIGITS,
    OCTAL_DIGITS,
    HashCommentsMixin,
    scan_string,
    scan_triple_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["TomlStateMachineLexer"]


_BOOL_VALUES: frozenset[str] = frozenset({"true", "false"})


class TomlStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """TOML lexer using composable mixins."""

    name = "toml"
    aliases = ()
    filenames = ("*.toml",)
    mimetypes = ("application/toml",)

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

            # Whitespace
            if char in " \t":
                start = pos
                while pos < length and code[pos] in " \t":
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start:pos], line, col)
                continue

            if char == "\n":
                yield Token(TokenType.WHITESPACE, char, line, col)
                pos += 1
                line += 1
                line_start = pos
                continue

            # Comments
            token, new_pos = self._try_hash_comment(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Section headers [[name]] or [name]
            if char == "[":
                start = pos
                if pos + 1 < length and code[pos + 1] == "[":
                    pos += 2
                    while pos < length and code[pos] != "]":
                        pos += 1
                    if pos + 1 < length and code[pos : pos + 2] == "]]":
                        pos += 2
                else:
                    pos += 1
                    while pos < length and code[pos] != "]":
                        pos += 1
                    if pos < length:
                        pos += 1
                yield Token(TokenType.NAME_TAG, code[start:pos], line, col)
                continue

            # Triple-quoted strings
            if char == '"' and pos + 2 < length and code[pos : pos + 3] == '"""':
                start = pos
                pos += 3
                pos, newlines = scan_triple_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                line += newlines
                if newlines:
                    line_start = start + code[start:pos].rfind("\n") + 1
                continue

            if char == "'" and pos + 2 < length and code[pos : pos + 3] == "'''":
                start = pos
                pos += 3
                # Literal triple string (no escapes)
                while pos < length:
                    if code[pos : pos + 3] == "'''":
                        pos += 3
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Regular strings
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Literal strings (no escapes)
            if char == "'":
                start = pos
                pos += 1
                while pos < length and code[pos] != "'":
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Numbers (including dates/times)
            if char in DIGITS or (char == "-" and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                token_type, pos = self._scan_toml_number(code, pos)
                yield Token(token_type, code[start:pos], line, col)
                continue

            if char == "+" and pos + 1 < length and code[pos + 1] in DIGITS:
                start = pos
                pos += 1
                token_type, pos = self._scan_toml_number(code, pos)
                yield Token(token_type, code[start:pos], line, col)
                continue

            # Booleans
            if char in "tf":
                for val in _BOOL_VALUES:
                    if code[pos : pos + len(val)] == val:
                        yield Token(TokenType.KEYWORD_CONSTANT, val, line, col)
                        pos += len(val)
                        break
                else:
                    # It's a key
                    start = pos
                    while pos < length and code[pos] not in "=\n#[]":
                        pos += 1
                    word = code[start:pos].rstrip()
                    yield Token(TokenType.NAME_ATTRIBUTE, word, line, col)
                    pos = start + len(word)
                continue

            # Keys
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_-"):
                    pos += 1
                word = code[start:pos]
                if word in _BOOL_VALUES:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                else:
                    yield Token(TokenType.NAME_ATTRIBUTE, word, line, col)
                continue

            # Punctuation
            if char in "=.,{}":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1

    def _scan_toml_number(self, code: str, pos: int) -> tuple[TokenType, int]:
        """Scan TOML number (including dates)."""
        length = len(code)
        start = pos

        if code[pos] in "+-":
            pos += 1

        # Check for special values
        if code[pos : pos + 3] in ("inf", "nan"):
            return TokenType.NUMBER_FLOAT, pos + 3

        # Hex/octal/binary
        if code[pos] == "0" and pos + 1 < length:
            next_char = code[pos + 1]
            if next_char in "xX":
                pos += 2
                while pos < length and (code[pos] in HEX_DIGITS or code[pos] == "_"):
                    pos += 1
                return TokenType.NUMBER_HEX, pos
            if next_char in "oO":
                pos += 2
                while pos < length and (code[pos] in OCTAL_DIGITS or code[pos] == "_"):
                    pos += 1
                return TokenType.NUMBER_OCT, pos
            if next_char in "bB":
                pos += 2
                while pos < length and (code[pos] in BINARY_DIGITS or code[pos] == "_"):
                    pos += 1
                return TokenType.NUMBER_BIN, pos

        # Decimal/date/time
        while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
            pos += 1

        # Check for date (YYYY-MM-DD)
        if pos < length and code[pos] == "-":
            temp = pos + 1
            while temp < length and code[temp] in DIGITS:
                temp += 1
            if temp > pos + 1 and temp < length and code[temp] == "-":
                # Likely a date
                pos = temp + 1
                while pos < length and code[pos] in DIGITS:
                    pos += 1
                # Time component?
                if pos < length and code[pos] in "T ":
                    pos += 1
                    while pos < length and code[pos] in DIGITS + ":":
                        pos += 1
                    # Fractional seconds
                    if pos < length and code[pos] == ".":
                        pos += 1
                        while pos < length and code[pos] in DIGITS:
                            pos += 1
                    # Timezone
                    if pos < length and code[pos] in "Z+-":
                        pos += 1
                        while pos < length and code[pos] in DIGITS + ":":
                            pos += 1
                return TokenType.LITERAL_DATE, pos

        # Float
        if pos < length and code[pos] == ".":
            pos += 1
            while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                pos += 1

        if pos < length and code[pos] in "eE":
            pos += 1
            if pos < length and code[pos] in "+-":
                pos += 1
            while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                pos += 1
            return TokenType.NUMBER_FLOAT, pos

        if "." in code[start:pos]:
            return TokenType.NUMBER_FLOAT, pos

        return TokenType.NUMBER_INTEGER, pos
