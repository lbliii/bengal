"""Hand-written Mojo lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
Mojo is a superset of Python with systems programming capabilities.
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

__all__ = ["MojoStateMachineLexer"]


# Python keywords plus Mojo-specific
_KEYWORDS: frozenset[str] = frozenset(
    {
        # Python keywords
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
        # Mojo-specific
        "fn",
        "let",
        "var",
        "struct",
        "trait",
        "alias",
        "owned",
        "borrowed",
        "inout",
        "raises",
        "capturing",
        "movable",
        "copyable",
        "register_passable",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "Int",
        "Int8",
        "Int16",
        "Int32",
        "Int64",
        "UInt",
        "UInt8",
        "UInt16",
        "UInt32",
        "UInt64",
        "Float16",
        "Float32",
        "Float64",
        "Bool",
        "String",
        "StringRef",
        "StringLiteral",
        "Pointer",
        "DType",
        "SIMD",
        "Tensor",
        "List",
        "Dict",
        "Set",
        "Tuple",
        "Optional",
        "Reference",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "print",
        "len",
        "range",
        "enumerate",
        "zip",
        "map",
        "filter",
        "isinstance",
        "type",
        "id",
        "hash",
        "abs",
        "min",
        "max",
        "sum",
        "ord",
        "chr",
        "hex",
        "oct",
        "bin",
        "int",
        "float",
        "str",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "slice",
        "object",
        "super",
        # Mojo builtins
        "rebind",
        "constrained",
        "parameter",
        "autotune",
        "simd_width",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"True", "False", "None"})


class MojoStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """Mojo lexer."""

    name = "mojo"
    aliases = ("🔥",)
    filenames = ("*.mojo", "*.🔥")
    mimetypes = ("text/x-mojo",)

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

            # Decorators @name
            if char == "@":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] in "_"):
                    pos += 1
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
                continue

            # Triple-quoted strings (docstrings)
            if char == '"' and pos + 2 < length and code[pos : pos + 3] == '"""':
                start = pos
                pos += 3
                pos, newlines = scan_triple_string(code, pos, '"')
                yield Token(TokenType.STRING_DOC, code[start:pos], line, col)
                if newlines:
                    line += newlines
                    line_start = start + code[start:pos].rfind("\n") + 1
                continue

            if char == "'" and pos + 2 < length and code[pos : pos + 3] == "'''":
                start = pos
                pos += 3
                while pos < length:
                    if code[pos : pos + 3] == "'''":
                        pos += 3
                        break
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.STRING_DOC, code[start:pos], line, col)
                continue

            # F-strings
            if char in "fFrRbB" and pos + 1 < length:
                prefix_start = pos
                prefixes = ""
                while pos < length and code[pos] in "fFrRbB":
                    prefixes += code[pos]
                    pos += 1
                if pos < length and code[pos] in "\"'":
                    quote = code[pos]
                    pos += 1
                    pos, _ = scan_string(code, pos, quote)
                    yield Token(TokenType.STRING, code[prefix_start:pos], line, col)
                    continue
                # Not a string, backtrack
                pos = prefix_start
                # Fall through to identifier

            # Regular strings
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            if char == "'":
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, "'")
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
                # Complex suffix
                if pos < length and code[pos] in "jJ":
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
                elif word in ("def", "fn", "class", "struct", "trait", "alias"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in ("import", "from", "as"):
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
            if char in "=<>!&|+-*/%^~@":
                start = pos
                if pos + 2 < length and code[pos : pos + 3] in ("**=", "//=", ">>=", "<<=", "@="):
                    pos += 3
                elif pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "&&",
                    "||",
                    "**",
                    "//",
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
                    "->",
                    ":=",
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Punctuation
            if char in "()[]{},.;:":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.TEXT, char, line, col)
            pos += 1
