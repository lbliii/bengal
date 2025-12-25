"""Dart lexer for Rosettes.

Thread-safe regex-based tokenizer for Dart source code.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["DartLexer"]

_KEYWORDS = (
    "abstract",
    "as",
    "assert",
    "async",
    "await",
    "break",
    "case",
    "catch",
    "class",
    "const",
    "continue",
    "covariant",
    "default",
    "deferred",
    "do",
    "dynamic",
    "else",
    "enum",
    "export",
    "extends",
    "extension",
    "external",
    "factory",
    "final",
    "finally",
    "for",
    "Function",
    "get",
    "hide",
    "if",
    "implements",
    "import",
    "in",
    "interface",
    "is",
    "late",
    "library",
    "mixin",
    "new",
    "on",
    "operator",
    "part",
    "required",
    "rethrow",
    "return",
    "sealed",
    "set",
    "show",
    "static",
    "super",
    "switch",
    "sync",
    "this",
    "throw",
    "try",
    "typedef",
    "var",
    "void",
    "while",
    "with",
    "yield",
)

_TYPES = (
    "bool",
    "double",
    "dynamic",
    "int",
    "num",
    "Object",
    "String",
    "void",
    "List",
    "Map",
    "Set",
    "Future",
    "Stream",
    "Iterable",
)

_CONSTANTS = ("true", "false", "null")


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in ("class", "enum", "extension", "mixin", "typedef", "var", "final", "const"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "export", "library", "part"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class DartLexer(PatternLexer):
    """Dart lexer. Thread-safe."""

    name = "dart"
    aliases = ()
    filenames = ("*.dart",)
    mimetypes = ("text/x-dart",)

    _WORD_PATTERN = r"\b[a-zA-Z_$][a-zA-Z0-9_$]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"///.*$", re.MULTILINE), TokenType.STRING_DOC),
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*\*[\s\S]*?\*/"), TokenType.STRING_DOC),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Annotations
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_DECORATOR),
        # Raw multi-line strings
        Rule(re.compile(r"r'''[\s\S]*?'''"), TokenType.STRING),
        Rule(re.compile(r'r"""[\s\S]*?"""'), TokenType.STRING),
        # Multi-line strings
        Rule(re.compile(r"'''[\s\S]*?'''"), TokenType.STRING),
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING),
        # Raw strings
        Rule(re.compile(r"r'[^']*'"), TokenType.STRING),
        Rule(re.compile(r'r"[^"]*"'), TokenType.STRING),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"\d+\.\d*(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\.\d+(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[eE][+-]?\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"=>|->|\.\.\.?|\?\?|\.\.|\?\."), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<<|>>>|>>"), TokenType.OPERATOR),
        Rule(re.compile(r"\?\?=|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|>>>=|~/="), TokenType.OPERATOR),
        Rule(re.compile(r"\+\+|--|~/"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!~<>=?:]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
