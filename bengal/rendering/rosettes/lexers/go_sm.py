"""Hand-written Go lexer using composable scanner mixins.

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
    scan_identifier,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["GoStateMachineLexer"]


# =============================================================================
# Language-specific data
# =============================================================================

_KEYWORDS: frozenset[str] = frozenset(
    {
        "break",
        "case",
        "chan",
        "const",
        "continue",
        "default",
        "defer",
        "else",
        "fallthrough",
        "for",
        "func",
        "go",
        "goto",
        "if",
        "import",
        "interface",
        "map",
        "package",
        "range",
        "return",
        "select",
        "struct",
        "switch",
        "type",
        "var",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "nil", "iota"})

_TYPES: frozenset[str] = frozenset(
    {
        "bool",
        "byte",
        "complex64",
        "complex128",
        "error",
        "float32",
        "float64",
        "int",
        "int8",
        "int16",
        "int32",
        "int64",
        "rune",
        "string",
        "uint",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "uintptr",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "append",
        "cap",
        "clear",
        "close",
        "complex",
        "copy",
        "delete",
        "imag",
        "len",
        "make",
        "max",
        "min",
        "new",
        "panic",
        "print",
        "println",
        "real",
        "recover",
    }
)


class GoStateMachineLexer(
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    StateMachineLexer,
):
    """Go lexer using composable mixins."""

    name = "go"
    aliases = ("golang",)
    filenames = ("*.go",)
    mimetypes = ("text/x-go",)

    # Go has imaginary numbers (1i)
    NUMBER_CONFIG = NumberConfig(
        imaginary_suffix="i",
    )

    # Go operators
    OPERATOR_CONFIG = OperatorConfig(
        three_char=frozenset({"<<=", ">>=", "&^=", "..."}),
        two_char=frozenset(
            {
                "==",
                "!=",
                "<=",
                ">=",
                "&&",
                "||",
                "<<",
                ">>",
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
                ":=",
                "<-",
                "&^",
            }
        ),
        one_char=frozenset("+-*/%&|^~!<>="),
    )

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> Iterator[Token]:
        """Tokenize Go source code."""
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

            # Raw strings (backtick)
            if char == "`":
                start = pos
                pos += 1
                start_line = line
                while pos < length and code[pos] != "`":
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                if pos < length:
                    pos += 1  # Include closing backtick
                yield Token(TokenType.STRING, code[start:pos], start_line, col)
                continue

            # Regular strings
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Runes (character literals)
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

            # Unknown
            yield Token(TokenType.ERROR, char, line, col)
            pos += 1

    def _classify_word(self, word: str) -> TokenType:
        """Classify an identifier."""
        if word in _KEYWORDS:
            if word in ("func", "type", "struct", "interface", "const", "var"):
                return TokenType.KEYWORD_DECLARATION
            if word in ("import", "package"):
                return TokenType.KEYWORD_NAMESPACE
            return TokenType.KEYWORD

        if word in _CONSTANTS:
            return TokenType.KEYWORD_CONSTANT

        if word in _TYPES:
            return TokenType.KEYWORD_TYPE

        if word in _BUILTINS:
            return TokenType.NAME_BUILTIN

        # Convention: exported names start with uppercase
        if word and word[0].isupper():
            return TokenType.NAME_CLASS

        return TokenType.NAME
