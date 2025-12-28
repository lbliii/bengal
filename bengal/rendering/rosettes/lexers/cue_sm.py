"""Hand-written CUE lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
CUE is a constraint-based configuration language.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    HEX_DIGITS,
    OCTAL_DIGITS,
    CStyleCommentsMixin,
    scan_string,
    scan_triple_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["CueStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "if",
        "for",
        "in",
        "let",
        "package",
        "import",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "string",
        "bytes",
        "bool",
        "int",
        "float",
        "number",
        "null",
        "int8",
        "int16",
        "int32",
        "int64",
        "int128",
        "uint",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "uint128",
        "float32",
        "float64",
        "rune",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "len",
        "close",
        "and",
        "or",
        "div",
        "mod",
        "quo",
        "rem",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "null", "_|_"})


class CueStateMachineLexer(
    CStyleCommentsMixin,
    StateMachineLexer,
):
    """CUE lexer."""

    name = "cue"
    aliases = ()
    filenames = ("*.cue",)
    mimetypes = ("text/x-cue",)

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = start

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

            # Comments
            token, new_pos = self._try_comment(code, pos, line, col)
            if token:
                if token.type == TokenType.COMMENT_MULTILINE:
                    newlines = token.value.count("\n")
                    if newlines:
                        line += newlines
                        line_start = pos + token.value.rfind("\n") + 1
                yield token
                pos = new_pos
                continue

            # Attributes @name(...)
            if char == "@":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                if pos < length and code[pos] == "(":
                    depth = 1
                    pos += 1
                    while pos < length and depth > 0:
                        if code[pos] == "(":
                            depth += 1
                        elif code[pos] == ")":
                            depth -= 1
                        pos += 1
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # Bottom value _|_
            if char == "_" and pos + 2 < length and code[pos : pos + 3] == "_|_":
                yield Token(TokenType.KEYWORD_CONSTANT, "_|_", line, col)
                pos += 3
                continue

            # Triple-quoted strings #"""..."""#
            if char == "#" and pos + 3 < length and code[pos + 1 : pos + 4] == '"""':
                start = pos
                pos += 4
                while pos < length:
                    if code[pos : pos + 4] == '"""#':
                        pos += 4
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Regular triple-quoted strings
            if char == '"' and pos + 2 < length and code[pos : pos + 3] == '"""':
                start = pos
                pos += 3
                pos, newlines = scan_triple_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                if newlines:
                    line += newlines
                    line_start = start + code[start:pos].rfind("\n") + 1
                continue

            # Raw strings #"..."#
            if char == "#" and pos + 1 < length and code[pos + 1] == '"':
                start = pos
                pos += 2
                while pos < length:
                    if code[pos] == '"' and pos + 1 < length and code[pos + 1] == "#":
                        pos += 2
                        break
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Bytes literals '...'
            if char == "'":
                start = pos
                pos += 1
                while pos < length and code[pos] != "'":
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    pos += 1
                if pos < length:
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

            # Numbers
            if char in DIGITS or (char == "." and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                if code[pos] == "0" and pos + 1 < length:
                    next_char = code[pos + 1]
                    if next_char in "xX":
                        pos += 2
                        while pos < length and (code[pos] in HEX_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_HEX, code[start:pos], line, col)
                        continue
                    if next_char in "oO":
                        pos += 2
                        while pos < length and (code[pos] in OCTAL_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_OCT, code[start:pos], line, col)
                        continue

                if char == ".":
                    pos += 1
                while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                    pos += 1
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
                # Multiplier suffixes
                if pos < length and code[pos] in "KMGTPE":
                    pos += 1
                    if pos < length and code[pos] == "i":
                        pos += 1

                value = code[start:pos]
                token_type = (
                    TokenType.NUMBER_FLOAT
                    if "." in value or "e" in value.lower()
                    else TokenType.NUMBER_INTEGER
                )
                yield Token(token_type, value, line, col)
                continue

            # Keywords, types and identifiers
            if char.isalpha() or char == "_" or char == "#":
                start = pos
                if char == "#":
                    pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                word = code[start:pos]
                if word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in ("package", "import"):
                    yield Token(TokenType.KEYWORD_NAMESPACE, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _TYPES or word.startswith("#"):
                    yield Token(TokenType.KEYWORD_TYPE, word, line, col)
                elif word in _BUILTINS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char in "=<>!&|+-*/?:":
                start = pos
                if pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "&&",
                    "||",
                    "=~",
                    "!~",
                    "::",
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Punctuation
            if char in "()[]{},.;":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
