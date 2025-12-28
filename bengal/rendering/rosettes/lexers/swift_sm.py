"""Hand-written Swift lexer using composable scanner mixins.

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
    scan_line_comment,
    scan_string,
    scan_triple_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["SwiftStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "actor",
        "any",
        "as",
        "associatedtype",
        "async",
        "await",
        "break",
        "case",
        "catch",
        "class",
        "continue",
        "default",
        "defer",
        "deinit",
        "do",
        "else",
        "enum",
        "extension",
        "fallthrough",
        "fileprivate",
        "for",
        "func",
        "guard",
        "if",
        "import",
        "in",
        "init",
        "inout",
        "internal",
        "is",
        "let",
        "macro",
        "nonisolated",
        "open",
        "operator",
        "precedencegroup",
        "private",
        "protocol",
        "public",
        "repeat",
        "rethrows",
        "return",
        "self",
        "Self",
        "some",
        "static",
        "struct",
        "subscript",
        "super",
        "switch",
        "throw",
        "throws",
        "try",
        "typealias",
        "var",
        "where",
        "while",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "Any",
        "AnyObject",
        "Array",
        "Bool",
        "Character",
        "Dictionary",
        "Double",
        "Float",
        "Int",
        "Int8",
        "Int16",
        "Int32",
        "Int64",
        "Never",
        "Optional",
        "Result",
        "Set",
        "String",
        "UInt",
        "UInt8",
        "UInt16",
        "UInt32",
        "UInt64",
        "Void",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "nil"})


class SwiftStateMachineLexer(
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    StateMachineLexer,
):
    """Swift lexer using composable mixins."""

    name = "swift"
    aliases = ()
    filenames = ("*.swift",)
    mimetypes = ("text/x-swift",)

    NUMBER_CONFIG = NumberConfig()

    OPERATOR_CONFIG = OperatorConfig(
        three_char=frozenset({"...", "..<", "===", "!=="}),
        two_char=frozenset(
            {
                "->",
                "..",
                "&&",
                "||",
                "==",
                "!=",
                "<=",
                ">=",
                "<<",
                ">>",
                "??",
                "?.",
                "+=",
                "-=",
                "*=",
                "/=",
                "%=",
                "&=",
                "|=",
                "^=",
                "<<=",
                ">>=",
            }
        ),
        one_char=frozenset("+-*/%&|^~<>=?!"),
    )

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

            # Attributes
            if char == "@":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # Preprocessor directives
            if char == "#":
                start = pos
                pos = scan_line_comment(code, pos)
                yield Token(TokenType.COMMENT_PREPROC, code[start:pos], line, col)
                continue

            # Triple-quoted strings
            if char == '"' and pos + 2 < length and code[pos : pos + 3] == '"""':
                start = pos
                pos += 3
                pos, newlines = scan_triple_string(code, pos, '"')
                yield Token(TokenType.STRING_DOC, code[start:pos], line, col)
                if newlines:
                    line += newlines
                    line_start = start + code[start:pos].rfind("\n") + 1
                continue

            # Regular strings
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
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
        if word in (
            "class",
            "struct",
            "enum",
            "protocol",
            "extension",
            "func",
            "var",
            "let",
            "typealias",
            "actor",
        ):
            return TokenType.KEYWORD_DECLARATION
        if word in ("import",):
            return TokenType.KEYWORD_NAMESPACE
        if word in _KEYWORDS:
            return TokenType.KEYWORD
        if word in _TYPES:
            return TokenType.KEYWORD_TYPE
        if word and word[0].isupper():
            return TokenType.NAME_CLASS
        return TokenType.NAME
