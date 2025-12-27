"""Hand-written Dart lexer using composable scanner mixins.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    IDENT_START,
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    NumberConfig,
    OperatorConfig,
    scan_block_comment,
    scan_identifier,
    scan_string,
    scan_triple_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["DartStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "abstract",
        "as",
        "assert",
        "async",
        "await",
        "base",
        "break",
        "case",
        "catch",
        "class",
        "const",
        "continue",
        "covariant",
        "default",
        "deferred",
        "do",
        "dynamic",
        "else",
        "enum",
        "export",
        "extends",
        "extension",
        "external",
        "factory",
        "final",
        "finally",
        "for",
        "Function",
        "get",
        "hide",
        "if",
        "implements",
        "import",
        "in",
        "interface",
        "is",
        "late",
        "library",
        "mixin",
        "new",
        "on",
        "operator",
        "part",
        "required",
        "rethrow",
        "return",
        "sealed",
        "set",
        "show",
        "static",
        "super",
        "switch",
        "sync",
        "this",
        "throw",
        "try",
        "typedef",
        "var",
        "when",
        "while",
        "with",
        "yield",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "bool",
        "double",
        "int",
        "num",
        "Object",
        "String",
        "void",
        "dynamic",
        "Future",
        "Stream",
        "List",
        "Map",
        "Set",
        "Iterable",
        "Function",
        "Never",
        "Null",
        "Type",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "null"})


class DartStateMachineLexer(
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    StateMachineLexer,
):
    """Dart lexer using composable mixins."""

    name = "dart"
    aliases = ()
    filenames = ("*.dart",)
    mimetypes = ("application/dart", "text/x-dart")

    NUMBER_CONFIG = NumberConfig()

    OPERATOR_CONFIG = OperatorConfig(
        three_char=frozenset({"??=", ">>>"}),
        two_char=frozenset(
            {
                "=>",
                "==",
                "!=",
                "<=",
                ">=",
                "&&",
                "||",
                "++",
                "--",
                "+=",
                "-=",
                "*=",
                "/=",
                "%=",
                "&=",
                "|=",
                "^=",
                "~/",
                "??",
                "?.",
                "..",
                "<<",
                ">>",
            }
        ),
        one_char=frozenset("+-*/%&|^~!<>=?"),
    )

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
            if char == "/" and pos + 1 < length:
                next_char = code[pos + 1]
                if next_char == "/":
                    start = pos
                    while pos < length and code[pos] != "\n":
                        pos += 1
                    yield Token(TokenType.COMMENT_SINGLE, code[start:pos], line, col)
                    continue
                if next_char == "*":
                    start = pos
                    is_doc = pos + 2 < length and code[pos + 2] == "*"
                    pos = scan_block_comment(code, pos + 2, "*/")
                    value = code[start:pos]
                    newlines = value.count("\n")
                    token_type = TokenType.STRING_DOC if is_doc else TokenType.COMMENT_MULTILINE
                    yield Token(token_type, value, line, col)
                    if newlines:
                        line += newlines
                        line_start = start + value.rfind("\n") + 1
                    continue

            # Annotations
            if char == "@":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] in "_."):
                    pos += 1
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # Triple-quoted strings
            if char in "\"'" and pos + 2 < length and code[pos : pos + 3] == char * 3:
                start = pos
                quote = char
                pos += 3
                pos, newlines = scan_triple_string(code, pos, quote)
                yield Token(TokenType.STRING, code[start:pos], line, col)
                if newlines:
                    line += newlines
                    line_start = start + code[start:pos].rfind("\n") + 1
                continue

            # Raw strings r"..." or r'...'
            if char == "r" and pos + 1 < length and code[pos + 1] in "\"'":
                start = pos
                quote = code[pos + 1]
                pos += 2
                while pos < length and code[pos] != quote:
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Regular strings
            if char in "\"'":
                start = pos
                quote = char
                pos += 1
                pos, _ = scan_string(code, pos, quote)
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Numbers
            token, new_pos = self._try_number(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Identifiers
            if char in IDENT_START:
                start = pos
                pos = scan_identifier(code, pos)
                word = code[start:pos]
                token_type = self._classify_word(word)
                yield Token(token_type, word, line, col)
                continue

            # Cascade notation ..
            if char == "." and pos + 1 < length and code[pos + 1] == ".":
                yield Token(TokenType.OPERATOR, "..", line, col)
                pos += 2
                continue

            # Operators
            token, new_pos = self._try_operator(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Punctuation
            if char in "()[]{}:;,.":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1

    def _classify_word(self, word: str) -> TokenType:
        if word in _CONSTANTS:
            return TokenType.KEYWORD_CONSTANT
        if word in ("class", "mixin", "enum", "extension", "typedef"):
            return TokenType.KEYWORD_DECLARATION
        if word in ("import", "export", "library", "part"):
            return TokenType.KEYWORD_NAMESPACE
        if word in _KEYWORDS:
            return TokenType.KEYWORD
        if word in _TYPES:
            return TokenType.KEYWORD_TYPE
        if word and word[0].isupper():
            return TokenType.NAME_CLASS
        return TokenType.NAME
