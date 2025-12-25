"""Triton lexer for Rosettes.

Thread-safe regex-based tokenizer for OpenAI's Triton GPU programming language.
Triton is a Python-like language for writing GPU kernels.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["TritonLexer"]

# Triton uses Python syntax with special decorators and intrinsics
_KEYWORDS = (
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
)

_TYPES = (
    # Triton types
    "int1",
    "int8",
    "int16",
    "int32",
    "int64",
    "uint8",
    "uint16",
    "uint32",
    "uint64",
    "float8",
    "float16",
    "float32",
    "float64",
    "bfloat16",
    "pointer_type",
    "block_type",
    "function_type",
    # Python types
    "int",
    "float",
    "bool",
    "str",
    "None",
)

_TRITON_BUILTINS = (
    # Triton intrinsics (tl.*)
    "load",
    "store",
    "atomic_cas",
    "atomic_xchg",
    "atomic_add",
    "atomic_max",
    "atomic_min",
    "atomic_and",
    "atomic_or",
    "atomic_xor",
    "arange",
    "zeros",
    "full",
    "broadcast_to",
    "reshape",
    "ravel",
    "expand_dims",
    "view",
    "cat",
    "split",
    "trans",
    "dot",
    "sum",
    "max",
    "min",
    "argmax",
    "argmin",
    "cumsum",
    "abs",
    "exp",
    "exp2",
    "log",
    "log2",
    "sqrt",
    "rsqrt",
    "sin",
    "cos",
    "sigmoid",
    "softmax",
    "relu",
    "gelu",
    "tanh",
    "erf",
    "where",
    "maximum",
    "minimum",
    "clamp",
    "floor",
    "ceil",
    "round",
    "trunc",
    "program_id",
    "num_programs",
    "cdiv",
    "static_assert",
    "static_print",
    "device_assert",
    "device_print",
    "multiple_of",
    "max_contiguous",
    "max_constant",
    "constexpr",
    "inline",
    "noinline",
    # Common Python builtins
    "print",
    "range",
    "len",
    "enumerate",
    "zip",
    "isinstance",
    "type",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("True", "False", "None"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("def", "class"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "from", "as"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word in _TRITON_BUILTINS:
        return TokenType.NAME_BUILTIN
    if word.startswith("BLOCK") or word.isupper():
        return TokenType.NAME_CONSTANT  # Constants like BLOCK_SIZE
    return TokenType.NAME


class TritonLexer(PatternLexer):
    """Triton lexer. Thread-safe."""

    name = "triton"
    aliases = ()
    filenames = ("*.triton",)
    mimetypes = ("text/x-triton",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Triton decorators (special)
        Rule(
            re.compile(r"@triton\.jit|@triton\.autotune|@triton\.heuristics"),
            TokenType.NAME_DECORATOR,
        ),
        # Python decorators
        Rule(
            re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*"),
            TokenType.NAME_DECORATOR,
        ),
        # Triton namespace (tl.)
        Rule(re.compile(r"\btl\.[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_BUILTIN),
        Rule(re.compile(r"\btriton\.[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_BUILTIN),
        # Triple-quoted strings
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING_DOC),
        Rule(re.compile(r"'''[\s\S]*?'''"), TokenType.STRING_DOC),
        # F-strings
        Rule(re.compile(r'f"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_INTERPOL),
        Rule(re.compile(r"f'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_INTERPOL),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[oO][0-7_]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"0[bB][01_]+"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?\d[\d_]*"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"//|<<|>>|\*\*|->"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<|>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|//=|%=|@=|&=|\|=|\^=|>>=|<<=|\*\*="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^~<>=!@]"), TokenType.OPERATOR),
        # Index/slice syntax (important for Triton)
        Rule(re.compile(r":"), TokenType.PUNCTUATION),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
