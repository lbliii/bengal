"""Hand-written R lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    HEX_DIGITS,
    HashCommentsMixin,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["RStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "if",
        "else",
        "repeat",
        "while",
        "function",
        "for",
        "in",
        "next",
        "break",
        "return",
    }
)

_CONSTANTS: frozenset[str] = frozenset(
    {
        "TRUE",
        "FALSE",
        "NULL",
        "NA",
        "NA_integer_",
        "NA_real_",
        "NA_complex_",
        "NA_character_",
        "Inf",
        "NaN",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "c",
        "list",
        "vector",
        "matrix",
        "array",
        "data.frame",
        "factor",
        "length",
        "names",
        "dim",
        "nrow",
        "ncol",
        "class",
        "typeof",
        "mode",
        "print",
        "cat",
        "paste",
        "paste0",
        "sprintf",
        "format",
        "sum",
        "mean",
        "median",
        "var",
        "sd",
        "min",
        "max",
        "range",
        "abs",
        "sqrt",
        "log",
        "log10",
        "log2",
        "exp",
        "sin",
        "cos",
        "tan",
        "round",
        "floor",
        "ceiling",
        "trunc",
        "which",
        "any",
        "all",
        "ifelse",
        "switch",
        "apply",
        "lapply",
        "sapply",
        "mapply",
        "tapply",
        "vapply",
        "library",
        "require",
        "source",
        "setwd",
        "getwd",
        "read.csv",
        "read.table",
        "write.csv",
        "write.table",
        "plot",
        "hist",
        "barplot",
        "boxplot",
        "pie",
        "lines",
        "points",
        "lm",
        "glm",
        "anova",
        "t.test",
        "chisq.test",
        "cor",
        "cov",
    }
)


class RStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """R lexer."""

    name = "r"
    aliases = ("R", "rlang")
    filenames = ("*.R", "*.r", "*.Rmd")
    mimetypes = ("text/x-r",)

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = 0

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

            # Strings
            if char in "\"'":
                start = pos
                quote = char
                pos += 1
                while pos < length and code[pos] != quote:
                    if code[pos] == "\\" and pos + 1 < length:
                        pos += 2
                        continue
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Raw strings r"..." or R"(...)"
            if char in "rR" and pos + 1 < length and code[pos + 1] == '"':
                start = pos
                pos += 2
                # Find delimiter for raw strings like R"(content)"
                if pos < length and code[pos] == "(":
                    pos += 1
                    while pos < length:
                        if code[pos : pos + 2] == ')"':
                            pos += 2
                            break
                        if code[pos] == "\n":
                            line += 1
                            line_start = pos + 1
                        pos += 1
                else:
                    while pos < length and code[pos] != '"':
                        if code[pos] == "\n":
                            line += 1
                            line_start = pos + 1
                        pos += 1
                    if pos < length:
                        pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS or (char == "." and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                if code[pos] == "0" and pos + 1 < length and code[pos + 1] in "xX":
                    pos += 2
                    while pos < length and code[pos] in HEX_DIGITS:
                        pos += 1
                    if pos < length and code[pos] == "L":
                        pos += 1
                    yield Token(TokenType.NUMBER_HEX, code[start:pos], line, col)
                    continue

                if char == ".":
                    pos += 1
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
                # Type suffixes
                if pos < length and code[pos] in "Li":
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
            if char.isalpha() or char in "_." or char == "`":
                if char == "`":  # Backtick quoted identifiers
                    start = pos
                    pos += 1
                    while pos < length and code[pos] != "`":
                        pos += 1
                    if pos < length:
                        pos += 1
                    yield Token(TokenType.NAME, code[start:pos], line, col)
                    continue

                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] in "_."):
                    pos += 1
                word = code[start:pos]
                if word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in ("function",):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in ("library", "require", "source"):
                    yield Token(TokenType.KEYWORD_NAMESPACE, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _BUILTINS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char in "=<>!&|+-*/%^~$@":
                start = pos
                if pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "&&",
                    "||",
                    "<<",
                    ">>",
                    "<-",
                    "->",
                    "%%",
                    "%*%",
                    "%/%",
                    "%in%",
                    "%o%",
                    "%x%",
                    "::",
                    ":::",
                ):
                    pos += 2
                    if (
                        code[start:pos] in ("::", ":::")
                        and pos + 1 < length
                        and code[pos : pos + 1] == ":"
                    ):
                        pos += 1
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Range/sequence :
            if char == ":":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Punctuation
            if char in "()[]{}:;,":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
