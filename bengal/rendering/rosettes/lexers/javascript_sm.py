"""Hand-written JavaScript lexer using composable scanner mixins.

Demonstrates how reusable components reduce code significantly.
O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    IDENT_START_DOLLAR,
    # Mixins
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    CStyleStringsMixin,
    # Configuration
    NumberConfig,
    OperatorConfig,
    StringConfig,
    # Helpers
    scan_identifier,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["JavaScriptStateMachineLexer"]


# =============================================================================
# Language-specific data (the only truly unique part)
# =============================================================================

_KEYWORDS: frozenset[str] = frozenset(
    {
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
    }
)

_RESERVED: frozenset[str] = frozenset(
    {
        "enum",
        "implements",
        "interface",
        "package",
        "private",
        "protected",
        "public",
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
        "Reflect",
        "RegExp",
        "Set",
        "String",
        "Symbol",
        "WeakMap",
        "WeakSet",
        "console",
        "document",
        "window",
        "globalThis",
        "parseInt",
        "parseFloat",
        "isNaN",
        "isFinite",
        "encodeURI",
        "decodeURI",
        "encodeURIComponent",
        "decodeURIComponent",
        "setTimeout",
        "setInterval",
        "clearTimeout",
        "clearInterval",
        "fetch",
        "require",
        "module",
        "exports",
    }
)


# =============================================================================
# Lexer implementation using mixins
# =============================================================================


class JavaScriptStateMachineLexer(
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleStringsMixin,
    CStyleOperatorsMixin,
    StateMachineLexer,
):
    """JavaScript/ECMAScript lexer using composable mixins.

    Most scanning logic is inherited from mixins.
    Only language-specific parts are implemented here.
    """

    name = "javascript"
    aliases = ("js", "ecmascript")
    filenames = ("*.js", "*.mjs", "*.cjs")
    mimetypes = ("text/javascript", "application/javascript")

    # Configure number scanning (JavaScript has BigInt with 'n' suffix)
    NUMBER_CONFIG = NumberConfig(
        integer_suffixes=("n",),  # BigInt
    )

    # Configure string scanning (JavaScript has template literals)
    STRING_CONFIG = StringConfig(
        backtick=True,  # Template literals
    )

    # Configure operators
    OPERATOR_CONFIG = OperatorConfig(
        three_char=frozenset({"===", "!==", ">>>", "**=", "&&=", "||=", "??="}),
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
            }
        ),
        one_char=frozenset("+-*/%&|^~!<>=?:."),
    )

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> Iterator[Token]:
        """Tokenize JavaScript source code."""
        pos = start
        length = end if end is not None else len(code)
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

            # Comments (// and /* */)
            token, new_pos = self._try_comment(code, pos, line, col)
            if token:
                # Track newlines in block comments
                if token.type == TokenType.COMMENT_MULTILINE:
                    newlines = token.value.count("\n")
                    if newlines:
                        line += newlines
                        line_start = pos + token.value.rfind("\n") + 1
                yield token
                pos = new_pos
                continue

            # Strings (", ', `)
            token, new_pos, newlines = self._try_string(code, pos, line, col)
            if token:
                if newlines:
                    line += newlines
                    line_start = pos + token.value.rfind("\n") + 1
                yield token
                pos = new_pos
                continue

            # Numbers
            token, new_pos = self._try_number(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Identifiers (including keywords and builtins)
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

            # Unknown
            yield Token(TokenType.ERROR, char, line, col)
            pos += 1

    def _classify_word(self, word: str) -> TokenType:
        """Classify an identifier."""
        if word in _KEYWORDS:
            if word in ("function", "class", "const", "let", "var"):
                return TokenType.KEYWORD_DECLARATION
            if word in ("import", "export", "from"):
                return TokenType.KEYWORD_NAMESPACE
            return TokenType.KEYWORD

        if word in _CONSTANTS:
            return TokenType.KEYWORD_CONSTANT

        if word in _RESERVED:
            return TokenType.KEYWORD_RESERVED

        if word in _BUILTINS:
            return TokenType.NAME_BUILTIN

        return TokenType.NAME
