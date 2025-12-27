"""Hand-written Java lexer using composable scanner mixins.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    IDENT_START_DOLLAR,
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

__all__ = ["JavaStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "abstract",
        "assert",
        "break",
        "case",
        "catch",
        "class",
        "const",
        "continue",
        "default",
        "do",
        "else",
        "enum",
        "extends",
        "final",
        "finally",
        "for",
        "goto",
        "if",
        "implements",
        "import",
        "instanceof",
        "interface",
        "native",
        "new",
        "package",
        "private",
        "protected",
        "public",
        "return",
        "static",
        "strictfp",
        "super",
        "switch",
        "synchronized",
        "this",
        "throw",
        "throws",
        "transient",
        "try",
        "volatile",
        "while",
        "yield",
        "var",
        "record",
        "sealed",
        "non-sealed",
        "permits",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "boolean",
        "byte",
        "char",
        "double",
        "float",
        "int",
        "long",
        "short",
        "void",
        "String",
        "Object",
        "Class",
        "Integer",
        "Long",
        "Double",
        "Float",
        "Boolean",
        "Character",
        "Byte",
        "Short",
        "Void",
        "List",
        "Map",
        "Set",
        "Collection",
        "ArrayList",
        "HashMap",
        "HashSet",
        "Optional",
        "Stream",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "null"})


class JavaStateMachineLexer(
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    StateMachineLexer,
):
    """Java lexer using composable mixins."""

    name = "java"
    aliases = ()
    filenames = ("*.java",)
    mimetypes = ("text/x-java",)

    NUMBER_CONFIG = NumberConfig(
        integer_suffixes=("l", "L"),
        float_suffixes=("f", "F", "d", "D"),
    )

    OPERATOR_CONFIG = OperatorConfig(
        three_char=frozenset({">>>", ">>=", "<<=", ">>>="}),
        two_char=frozenset(
            {
                "->",
                "++",
                "--",
                "&&",
                "||",
                "==",
                "!=",
                "<=",
                ">=",
                "<<",
                ">>",
                "+=",
                "-=",
                "*=",
                "/=",
                "%=",
                "&=",
                "|=",
                "^=",
            }
        ),
        one_char=frozenset("+-*/%&|^!~<>=?:"),
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

            # Comments (including Javadoc)
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
                    is_javadoc = pos + 2 < length and code[pos + 2] == "*"
                    pos = scan_block_comment(code, pos + 2, "*/")
                    value = code[start:pos]
                    newlines = value.count("\n")
                    token_type = TokenType.STRING_DOC if is_javadoc else TokenType.COMMENT_MULTILINE
                    yield Token(token_type, value, line, col)
                    if newlines:
                        line += newlines
                        line_start = start + value.rfind("\n") + 1
                    continue

            # Annotations
            if char == "@":
                start = pos
                pos += 1
                if pos < length and code[pos] in IDENT_START_DOLLAR:
                    pos = scan_identifier(code, pos, allow_dollar=True)
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # Text blocks (Java 15+)
            if char == '"' and pos + 2 < length and code[pos : pos + 3] == '"""':
                start = pos
                pos += 3
                pos, newlines = scan_triple_string(code, pos, '"')
                yield Token(TokenType.STRING_DOC, code[start:pos], line, col)
                if newlines:
                    line += newlines
                    line_start = start + code[start:pos].rfind("\n") + 1
                continue

            # Strings
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Characters
            if char == "'":
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, "'")
                yield Token(TokenType.STRING_CHAR, code[start:pos], line, col)
                continue

            # Numbers
            token, new_pos = self._try_number(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Identifiers
            if char in IDENT_START_DOLLAR:
                start = pos
                pos = scan_identifier(code, pos, allow_dollar=True)
                word = code[start:pos]
                token_type = self._classify_word(word)
                yield Token(token_type, word, line, col)
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
        if word in ("class", "interface", "enum", "record", "extends", "implements"):
            return TokenType.KEYWORD_DECLARATION
        if word in ("import", "package"):
            return TokenType.KEYWORD_NAMESPACE
        if word in _KEYWORDS:
            return TokenType.KEYWORD
        if word in _TYPES:
            return TokenType.KEYWORD_TYPE
        if word and word[0].isupper():
            return TokenType.NAME_CLASS
        return TokenType.NAME
