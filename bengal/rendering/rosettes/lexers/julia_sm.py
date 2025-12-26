"""Hand-written Julia lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    BINARY_DIGITS,
    DIGITS,
    HEX_DIGITS,
    OCTAL_DIGITS,
    HashCommentsMixin,
    scan_string,
    scan_triple_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["JuliaStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        "abstract",
        "baremodule",
        "begin",
        "break",
        "catch",
        "const",
        "continue",
        "do",
        "else",
        "elseif",
        "end",
        "export",
        "finally",
        "for",
        "function",
        "global",
        "if",
        "import",
        "in",
        "let",
        "local",
        "macro",
        "module",
        "mutable",
        "outer",
        "primitive",
        "quote",
        "return",
        "struct",
        "try",
        "type",
        "using",
        "where",
        "while",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "Any",
        "Bool",
        "Char",
        "Float16",
        "Float32",
        "Float64",
        "Int",
        "Int8",
        "Int16",
        "Int32",
        "Int64",
        "Int128",
        "Integer",
        "Number",
        "Real",
        "String",
        "UInt",
        "UInt8",
        "UInt16",
        "UInt32",
        "UInt64",
        "UInt128",
        "Array",
        "Dict",
        "Set",
        "Tuple",
        "Vector",
        "Matrix",
        "Nothing",
        "Missing",
    }
)

_CONSTANTS: frozenset[str] = frozenset(
    {
        "true",
        "false",
        "nothing",
        "missing",
        "Inf",
        "Inf16",
        "Inf32",
        "Inf64",
        "NaN",
        "NaN16",
        "NaN32",
        "NaN64",
        "pi",
        "π",
        "ℯ",
        "im",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "print",
        "println",
        "show",
        "display",
        "typeof",
        "sizeof",
        "length",
        "size",
        "eltype",
        "push!",
        "pop!",
        "append!",
        "insert!",
        "delete!",
        "map",
        "filter",
        "reduce",
        "sum",
        "prod",
        "maximum",
        "minimum",
        "sort",
        "sort!",
        "reverse",
        "reverse!",
        "collect",
        "range",
    }
)


class JuliaStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """Julia lexer."""

    name = "julia"
    aliases = ("jl",)
    filenames = ("*.jl",)
    mimetypes = ("text/x-julia", "application/x-julia")

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

            # Block comments #= ... =#
            if char == "#" and pos + 1 < length and code[pos + 1] == "=":
                start = pos
                pos += 2
                depth = 1
                start_line = line
                while pos < length and depth > 0:
                    if code[pos : pos + 2] == "#=":
                        depth += 1
                        pos += 2
                        continue
                    if code[pos : pos + 2] == "=#":
                        depth -= 1
                        pos += 2
                        continue
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.COMMENT_MULTILINE, code[start:pos], start_line, col)
                continue

            # Line comments
            token, new_pos = self._try_hash_comment(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Macros @name
            if char == "@":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] in "_!"):
                    pos += 1
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # Symbols :name
            if char == ":":
                if pos + 1 < length and (code[pos + 1].isalpha() or code[pos + 1] == "_"):
                    start = pos
                    pos += 1
                    while pos < length and (code[pos].isalnum() or code[pos] in "_!"):
                        pos += 1
                    yield Token(TokenType.STRING_SYMBOL, code[start:pos], line, col)
                    continue
                yield Token(TokenType.PUNCTUATION, ":", line, col)
                pos += 1
                continue

            # Triple-quoted strings
            if char == '"' and pos + 2 < length and code[pos : pos + 3] == '"""':
                start = pos
                pos += 3
                pos, newlines = scan_triple_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
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

            # Character literals
            if char == "'":
                start = pos
                pos += 1
                if pos < length and code[pos] == "\\":
                    pos += 2
                elif pos < length:
                    pos += 1
                if pos < length and code[pos] == "'":
                    pos += 1
                yield Token(TokenType.STRING_CHAR, code[start:pos], line, col)
                continue

            # Raw strings r"..."
            if char == "r" and pos + 1 < length and code[pos + 1] == '"':
                start = pos
                pos += 2
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
                # Imaginary suffix
                if pos < length and code[pos] == "im":
                    pos += 2
                value = code[start:pos]
                token_type = (
                    TokenType.NUMBER_FLOAT
                    if "." in value or "e" in value.lower()
                    else TokenType.NUMBER_INTEGER
                )
                yield Token(token_type, value, line, col)
                continue

            # Keywords and identifiers (Unicode allowed)
            if char.isalpha() or char == "_" or ord(char) > 127:
                start = pos
                while pos < length and (
                    code[pos].isalnum() or code[pos] in "_!" or ord(code[pos]) > 127
                ):
                    pos += 1
                word = code[start:pos]
                if word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in (
                    "function",
                    "struct",
                    "mutable",
                    "abstract",
                    "primitive",
                    "macro",
                    "module",
                ):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in ("import", "using", "export"):
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

            # Operators
            if char in "=<>!&|+-*/%^~÷∈∉∋∌⊆⊇⊂⊃∪∩":
                start = pos
                # Multi-char operators
                if pos + 2 < length and code[pos : pos + 3] in ("===", "!==", "<=>", ">>>"):
                    pos += 3
                elif pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "&&",
                    "||",
                    "<<",
                    ">>",
                    "+=",
                    "-=",
                    "*=",
                    "/=",
                    "^=",
                    "÷=",
                    "=>",
                    "->",
                    "::",
                    "..",
                    "<:",
                    ">:",
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Range operator
            if char == "." and pos + 1 < length and code[pos + 1] == ".":
                yield Token(TokenType.OPERATOR, "..", line, col)
                pos += 2
                continue

            # Punctuation
            if char in "()[]{},.;?":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
