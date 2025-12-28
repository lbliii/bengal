"""Hand-written Triton lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
Triton is a language/library for GPU kernel programming with Python.
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

__all__ = ["TritonStateMachineLexer"]


# Python keywords
_KEYWORDS: frozenset[str] = frozenset(
    {
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
    }
)

# Triton-specific types
_TYPES: frozenset[str] = frozenset(
    {
        "float16",
        "float32",
        "float64",
        "bfloat16",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "bool",
        "pointer_type",
        "block_type",
        "function_type",
    }
)

# Triton builtins and API
_BUILTINS: frozenset[str] = frozenset(
    {
        # Triton language constructs
        "tl",
        "triton",
        # Memory operations
        "load",
        "store",
        "atomic_add",
        "atomic_max",
        "atomic_min",
        "atomic_and",
        "atomic_or",
        "atomic_xor",
        "atomic_cas",
        # Tensor operations
        "arange",
        "zeros",
        "full",
        "broadcast",
        "broadcast_to",
        "reshape",
        "expand_dims",
        "view",
        "cat",
        "split",
        # Math operations
        "exp",
        "exp2",
        "log",
        "log2",
        "cos",
        "sin",
        "sqrt",
        "rsqrt",
        "abs",
        "floor",
        "ceil",
        "round",
        "clamp",
        "sigmoid",
        "softmax",
        # Reduction operations
        "sum",
        "max",
        "min",
        "argmax",
        "argmin",
        "reduce",
        # Control flow
        "program_id",
        "num_programs",
        "cdiv",
        # Comparison
        "where",
        "maximum",
        "minimum",
        # Data types
        "constexpr",
        # Python builtins used in Triton
        "print",
        "len",
        "range",
        "enumerate",
        "zip",
        "isinstance",
        "type",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"True", "False", "None"})

# Triton decorators
_DECORATORS: frozenset[str] = frozenset(
    {
        "triton.jit",
        "triton.autotune",
        "triton.heuristics",
        "jit",
        "autotune",
    }
)


class TritonStateMachineLexer(
    HashCommentsMixin,
    StateMachineLexer,
):
    """Triton lexer (Python-based GPU programming)."""

    name = "triton"
    aliases = ()
    filenames = ("*.triton",)
    mimetypes = ("text/x-triton",)

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = start

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

            # Decorators @triton.jit etc
            if char == "@":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] in "_."):
                    pos += 1
                yield Token(TokenType.NAME_DECORATOR, code[start:pos], line, col)
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
                elif word in ("def", "class"):
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
                if pos + 2 < length and code[pos : pos + 3] in ("**=", "//=", ">>=", "<<="):
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
