"""Go lexer for Rosettes.

Thread-safe regex-based tokenizer for Go source code.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["GoLexer"]

_KEYWORDS = (
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
)

_TYPES = (
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
)

_BUILTINS = (
    "append",
    "cap",
    "close",
    "complex",
    "copy",
    "delete",
    "imag",
    "len",
    "make",
    "new",
    "panic",
    "print",
    "println",
    "real",
    "recover",
)

_CONSTANTS = ("true", "false", "nil", "iota")


def _classify_keyword(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in ("func", "type", "struct", "interface", "const", "var"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "package"):
        return TokenType.KEYWORD_NAMESPACE
    return TokenType.KEYWORD


def _classify_name(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class GoLexer(PatternLexer):
    """Go lexer. Thread-safe."""

    name = "go"
    aliases = ("golang",)
    filenames = ("*.go",)
    mimetypes = ("text/x-go",)

    _KEYWORD_PATTERN = r"\b(?:" + "|".join(_KEYWORDS + _CONSTANTS) + r")\b"
    _NAME_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Raw strings
        Rule(re.compile(r"`[^`]*`"), TokenType.STRING),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Runes
        Rule(
            re.compile(r"'[^'\\]'|'\\.'|'\\x[0-9a-fA-F]{2}'|'\\u[0-9a-fA-F]{4}'"),
            TokenType.STRING_CHAR,
        ),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[oO][0-7_]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"0[bB][01_]+"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"\d[\d_]*\.[\d_]*(?:[eE][+-]?[\d_]+)?i?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?[\d_]+i?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*i"), TokenType.NUMBER_FLOAT),  # imaginary
        Rule(re.compile(r"\d[\d_]*"), TokenType.NUMBER_INTEGER),
        # Keywords
        Rule(re.compile(_KEYWORD_PATTERN), _classify_keyword),
        # Names
        Rule(re.compile(_NAME_PATTERN), _classify_name),
        # Operators
        Rule(re.compile(r":=|<-|\.\.\."), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<<|>>|&\^"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|&\^="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!<>=]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
