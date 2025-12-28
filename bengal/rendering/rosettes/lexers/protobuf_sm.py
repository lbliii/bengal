"""Hand-written Protocol Buffers lexer using composable scanner mixins.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    HEX_DIGITS,
    CStyleCommentsMixin,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["ProtobufStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "syntax",
        "import",
        "weak",
        "public",
        "package",
        "option",
        "optional",
        "required",
        "repeated",
        "group",
        "oneof",
        "map",
        "extensions",
        "to",
        "max",
        "reserved",
        "extend",
        "message",
        "enum",
        "service",
        "rpc",
        "stream",
        "returns",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "int32",
        "int64",
        "uint32",
        "uint64",
        "sint32",
        "sint64",
        "fixed32",
        "fixed64",
        "sfixed32",
        "sfixed64",
        "float",
        "double",
        "bool",
        "string",
        "bytes",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false"})


class ProtobufStateMachineLexer(
    CStyleCommentsMixin,
    StateMachineLexer,
):
    """Protocol Buffers lexer."""

    name = "protobuf"
    aliases = ("proto",)
    filenames = ("*.proto",)
    mimetypes = ("text/x-protobuf",)

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

            # Strings
            if char in "\"'":
                start = pos
                quote = char
                pos += 1
                pos, _ = scan_string(code, pos, quote)
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS or (char == "-" and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                if char == "-":
                    pos += 1
                if code[pos] == "0" and pos + 1 < length and code[pos + 1] in "xX":
                    pos += 2
                    while pos < length and code[pos] in HEX_DIGITS:
                        pos += 1
                    yield Token(TokenType.NUMBER_HEX, code[start:pos], line, col)
                    continue
                while pos < length and code[pos] in DIGITS:
                    pos += 1
                if pos < length and code[pos] == ".":
                    pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
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

            # Keywords and identifiers
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                word = code[start:pos]
                if word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in ("message", "enum", "service", "rpc", "oneof"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in ("package", "import", "option"):
                    yield Token(TokenType.KEYWORD_NAMESPACE, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _TYPES:
                    yield Token(TokenType.KEYWORD_TYPE, word, line, col)
                elif word and word[0].isupper():
                    yield Token(TokenType.NAME_CLASS, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char == "=":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Punctuation
            if char in "()[]{}:;,.":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1
