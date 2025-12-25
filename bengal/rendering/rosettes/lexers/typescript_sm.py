"""Hand-written TypeScript lexer using composable scanner mixins.

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
    scan_identifier,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["TypeScriptStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        # JavaScript keywords
        "async",
        "await",
        "break",
        "case",
        "catch",
        "class",
        "const",
        "continue",
        "debugger",
        "default",
        "delete",
        "do",
        "else",
        "export",
        "extends",
        "finally",
        "for",
        "function",
        "if",
        "import",
        "in",
        "instanceof",
        "let",
        "new",
        "of",
        "return",
        "static",
        "super",
        "switch",
        "this",
        "throw",
        "try",
        "typeof",
        "var",
        "void",
        "while",
        "with",
        "yield",
        # TypeScript-specific
        "abstract",
        "as",
        "asserts",
        "declare",
        "enum",
        "implements",
        "interface",
        "is",
        "keyof",
        "namespace",
        "override",
        "private",
        "protected",
        "public",
        "readonly",
        "type",
        "infer",
        "satisfies",
    }
)

_TYPE_KEYWORDS: frozenset[str] = frozenset(
    {
        "any",
        "boolean",
        "never",
        "null",
        "number",
        "object",
        "string",
        "symbol",
        "undefined",
        "unknown",
        "void",
        "bigint",
    }
)

_CONSTANTS: frozenset[str] = frozenset(
    {
        "true",
        "false",
        "null",
        "undefined",
        "NaN",
        "Infinity",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "Array",
        "Boolean",
        "Date",
        "Error",
        "Function",
        "JSON",
        "Map",
        "Math",
        "Number",
        "Object",
        "Promise",
        "Proxy",
        "Record",
        "RegExp",
        "Set",
        "String",
        "Symbol",
        "WeakMap",
        "WeakSet",
        "Partial",
        "Required",
        "Readonly",
        "Pick",
        "Omit",
        "Exclude",
        "Extract",
        "NonNullable",
        "Parameters",
        "ReturnType",
        "InstanceType",
        "console",
        "document",
        "window",
        "globalThis",
    }
)


class TypeScriptStateMachineLexer(
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    StateMachineLexer,
):
    """TypeScript lexer using composable mixins."""

    name = "typescript"
    aliases = ("ts",)
    filenames = ("*.ts", "*.tsx", "*.mts", "*.cts")
    mimetypes = ("text/typescript", "application/typescript")

    NUMBER_CONFIG = NumberConfig(integer_suffixes=("n",))

    OPERATOR_CONFIG = OperatorConfig(
        three_char=frozenset({"===", "!==", ">>>", "**=", "&&=", "||=", "??=", ">>>="}),
        two_char=frozenset(
            {
                "==",
                "!=",
                "<=",
                ">=",
                "&&",
                "||",
                "??",
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
                "<<",
                ">>",
                "=>",
                "**",
                "?.",
                "!.",
            }
        ),
        one_char=frozenset("+-*/%&|^~!<>=?:."),
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

            # Decorators
            if char == "@":
                start = pos
                pos += 1
                if pos < length and code[pos] in IDENT_START_DOLLAR:
                    pos = scan_identifier(code, pos, allow_dollar=True)
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # Template literals
            if char == "`":
                start = pos
                pos += 1
                start_line = line
                while pos < length and code[pos] != "`":
                    if code[pos] == "\\":
                        pos += 2
                        continue
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], start_line, col)
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

            # Spread/rest operator
            if char == "." and pos + 2 < length and code[pos : pos + 3] == "...":
                yield Token(TokenType.OPERATOR, "...", line, col)
                pos += 3
                continue

            # Operators
            token, new_pos = self._try_operator(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Punctuation (including angle brackets for generics)
            if char in "()[]{},.;<>":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1

    def _classify_word(self, word: str) -> TokenType:
        if word in _CONSTANTS:
            return TokenType.KEYWORD_CONSTANT
        if word in _TYPE_KEYWORDS:
            return TokenType.KEYWORD_TYPE
        if word in ("function", "class", "const", "let", "var", "type", "interface", "enum"):
            return TokenType.KEYWORD_DECLARATION
        if word in ("import", "export", "from", "namespace"):
            return TokenType.KEYWORD_NAMESPACE
        if word in _KEYWORDS:
            return TokenType.KEYWORD
        if word in _BUILTINS:
            return TokenType.NAME_BUILTIN
        return TokenType.NAME
