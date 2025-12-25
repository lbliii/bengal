"""Mojo lexer for Rosettes.

Thread-safe regex-based tokenizer for Mojo (🔥) source code.
Mojo is a Python superset designed for AI/ML by Modular.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["MojoLexer"]

# Mojo-specific keywords (in addition to Python)
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
    # Mojo-specific keywords
    "fn",
    "let",
    "var",
    "alias",
    "struct",
    "trait",
    "inout",
    "owned",
    "borrowed",
    "raises",
    "capturing",
    "parameter",
    "self",
    "Self",
)

_TYPES = (
    # Mojo built-in types
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
    "StringLiteral",
    "DType",
    "Tensor",
    "SIMD",
    "Pointer",
    "Reference",
    "Optional",
    "Tuple",
    "List",
    "Dict",
    "Set",
    "Slice",
    "Range",
    # Python types
    "int",
    "float",
    "str",
    "bool",
    "list",
    "dict",
    "set",
    "tuple",
    "None",
)

_BUILTINS = (
    "print",
    "len",
    "range",
    "enumerate",
    "zip",
    "map",
    "filter",
    "sorted",
    "reversed",
    "min",
    "max",
    "sum",
    "abs",
    "round",
    "isinstance",
    "type",
    "id",
    "hash",
    "repr",
    "str",
    "int",
    "float",
    "bool",
    "list",
    "dict",
    "set",
    "tuple",
    "ord",
    "chr",
    "hex",
    "oct",
    "bin",
    "format",
    "input",
    "open",
    "compile",
    "exec",
    "eval",
    "globals",
    "locals",
    "vars",
    "dir",
    # Mojo-specific
    "simd_width",
    "rebind",
    "constrained",
    "parameter",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("True", "False", "None"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("def", "fn", "class", "struct", "trait", "alias", "let", "var"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "from", "as"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class MojoLexer(PatternLexer):
    """Mojo lexer. Thread-safe."""

    name = "mojo"
    aliases = ("🔥",)
    filenames = ("*.mojo", "*.🔥")
    mimetypes = ("text/x-mojo",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Decorators
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_DECORATOR),
        # Triple-quoted strings (docstrings)
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING_DOC),
        Rule(re.compile(r"'''[\s\S]*?'''"), TokenType.STRING_DOC),
        # F-strings
        Rule(re.compile(r'f"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_INTERPOL),
        Rule(re.compile(r"f'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_INTERPOL),
        # Raw strings
        Rule(re.compile(r'r"[^"]*"'), TokenType.STRING),
        Rule(re.compile(r"r'[^']*'"), TokenType.STRING),
        # Byte strings
        Rule(re.compile(r'b"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        Rule(re.compile(r"b'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[oO][0-7_]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"0[bB][01_]+"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?[jJ]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?\d[\d_]*[jJ]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[jJ]?"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"->|=>|:=|@"), TokenType.OPERATOR),
        Rule(re.compile(r"//|<<|>>|\*\*"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<|>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|//=|%=|@=|&=|\|=|\^=|>>=|<<=|\*\*="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^~<>=!]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
