"""Scala lexer for Rosettes.

Thread-safe regex-based tokenizer for Scala source code.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["ScalaLexer"]

_KEYWORDS = (
    "abstract",
    "case",
    "catch",
    "class",
    "def",
    "derives",
    "do",
    "else",
    "enum",
    "export",
    "extends",
    "extension",
    "final",
    "finally",
    "for",
    "forSome",
    "given",
    "if",
    "implicit",
    "import",
    "infix",
    "inline",
    "lazy",
    "match",
    "new",
    "object",
    "opaque",
    "open",
    "override",
    "package",
    "private",
    "protected",
    "return",
    "sealed",
    "then",
    "throw",
    "trait",
    "transparent",
    "try",
    "type",
    "using",
    "val",
    "var",
    "while",
    "with",
    "yield",
)

_TYPES = (
    "Any",
    "AnyRef",
    "AnyVal",
    "Array",
    "Boolean",
    "Byte",
    "Char",
    "Double",
    "Float",
    "Int",
    "List",
    "Long",
    "Map",
    "Nothing",
    "Null",
    "Option",
    "Seq",
    "Set",
    "Short",
    "String",
    "Unit",
    "Vector",
)

_CONSTANTS = ("true", "false", "null", "this", "super")


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("true", "false", "null"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("this", "super"):
        return TokenType.KEYWORD_PSEUDO
    if word in ("class", "trait", "object", "enum", "def", "val", "var", "type", "given"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "package", "export"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class ScalaLexer(PatternLexer):
    """Scala lexer. Thread-safe."""

    name = "scala"
    aliases = ("sc",)
    filenames = ("*.scala", "*.sc")
    mimetypes = ("text/x-scala",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*\*[\s\S]*?\*/"), TokenType.STRING_DOC),  # ScalaDoc
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Annotations
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_DECORATOR),
        # Multi-line strings
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING_DOC),
        # String interpolation prefix
        Rule(re.compile(r'[srf]"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_INTERPOL),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Characters
        Rule(re.compile(r"'[^'\\]'|'\\.'|'\\u[0-9a-fA-F]{4}'"), TokenType.STRING_CHAR),
        # Symbols
        Rule(re.compile(r"'[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.STRING_SYMBOL),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+[lL]?"), TokenType.NUMBER_HEX),
        Rule(
            re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?[fFdD]?"), TokenType.NUMBER_FLOAT
        ),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?\d[\d_]*[fFdD]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[lLfFdD]?"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"=>|<-|->|<:|>:|#|@"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<<|>>>|>>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|>>>="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!~<>=?:]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
