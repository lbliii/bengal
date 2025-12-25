"""Hand-written Gleam lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
Gleam is a type-safe language for Erlang/BEAM.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    BINARY_DIGITS,
    DIGITS,
    HEX_DIGITS,
    OCTAL_DIGITS,
    CStyleCommentsMixin,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["GleamStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "as",
        "assert",
        "case",
        "const",
        "external",
        "fn",
        "if",
        "import",
        "let",
        "opaque",
        "pub",
        "todo",
        "try",
        "type",
        "use",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "Int",
        "Float",
        "Bool",
        "String",
        "Nil",
        "List",
        "Result",
        "Option",
        "BitString",
        "UtfCodepoint",
        "Dynamic",
        "Tuple",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "Ok",
        "Error",
        "Some",
        "None",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"True", "False", "Nil"})


class GleamStateMachineLexer(
    CStyleCommentsMixin,
    StateMachineLexer,
):
    """Gleam lexer."""

    name = "gleam"
    aliases = ()
    filenames = ("*.gleam",)
    mimetypes = ("text/x-gleam",)

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

            # Attributes @deprecated etc
            if char == "@":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # Strings
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS:
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
                    if next_char in "bB":
                        pos += 2
                        while pos < length and (code[pos] in BINARY_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_BIN, code[start:pos], line, col)
                        continue

                while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                    pos += 1
                if pos < length and code[pos] == ".":
                    if pos + 1 < length and code[pos + 1] in DIGITS:
                        pos += 1
                        while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                            pos += 1
                if pos < length and code[pos] in "eE":
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                        pos += 1

                value = code[start:pos]
                token_type = TokenType.NUMBER_FLOAT if "." in value else TokenType.NUMBER_INTEGER
                yield Token(token_type, value, line, col)
                continue

            # Keywords and identifiers
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                word = code[start:pos]
                if word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in ("fn", "type", "opaque", "const", "external"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in ("import", "pub"):
                    yield Token(TokenType.KEYWORD_NAMESPACE, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _TYPES:
                    yield Token(TokenType.KEYWORD_TYPE, word, line, col)
                elif word in _BUILTINS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                elif word and word[0].isupper():
                    yield Token(TokenType.NAME_CLASS, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Discard name
            if (
                char == "_"
                and pos + 1 < length
                and (code[pos + 1].isalpha() or code[pos + 1] == "_")
            ):
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                yield Token(TokenType.NAME, code[start:pos], line, col)
                continue

            # Operators
            if char in "=<>!|+-.*/":
                start = pos
                if pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "||",
                    "|>",
                    "->",
                    "<-",
                    "..",
                    "<>",
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Pipe operator
            if char == "|" and pos + 1 < length and code[pos + 1] == ">":
                yield Token(TokenType.OPERATOR, "|>", line, col)
                pos += 2
                continue

            # Punctuation
            if char in "()[]{}:,;#":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
