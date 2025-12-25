"""Pkl lexer for Rosettes.

Thread-safe regex-based tokenizer for Apple's Pkl configuration language.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["PklLexer"]

_KEYWORDS = (
    "abstract",
    "amends",
    "as",
    "class",
    "else",
    "extends",
    "external",
    "false",
    "for",
    "function",
    "hidden",
    "if",
    "import",
    "in",
    "is",
    "let",
    "local",
    "module",
    "new",
    "nothing",
    "null",
    "open",
    "out",
    "outer",
    "read",
    "super",
    "this",
    "throw",
    "trace",
    "true",
    "typealias",
    "unknown",
    "when",
)

_TYPES = (
    "Any",
    "Boolean",
    "Class",
    "Collection",
    "DataSize",
    "Duration",
    "Dynamic",
    "Float",
    "Int",
    "Int8",
    "Int16",
    "Int32",
    "UInt",
    "UInt8",
    "UInt16",
    "UInt32",
    "Listing",
    "Map",
    "Mapping",
    "Mixin",
    "Module",
    "Nothing",
    "Null",
    "Number",
    "Object",
    "Pair",
    "Regex",
    "Resource",
    "Set",
    "String",
    "Type",
    "TypeAlias",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("true", "false", "null", "nothing"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("class", "module", "function", "typealias", "let", "local"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "amends", "extends"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class PklLexer(PatternLexer):
    """Pkl lexer. Thread-safe."""

    name = "pkl"
    aliases = ()
    filenames = ("*.pkl",)
    mimetypes = ("text/x-pkl",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"///.*$", re.MULTILINE), TokenType.STRING_DOC),
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Annotations
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_DECORATOR),
        # Multi-line strings
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING),
        Rule(re.compile(r"#\"[\s\S]*?\"#"), TokenType.STRING),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Numbers with units
        Rule(
            re.compile(r"\d+\.\d*(?:[eE][+-]?\d+)?(?:\.(?:ns|us|ms|s|min|h|d|b|kb|mb|gb|tb|pb))?"),
            TokenType.NUMBER_FLOAT,
        ),
        Rule(
            re.compile(r"\d+(?:\.(?:ns|us|ms|s|min|h|d|b|kb|mb|gb|tb|pb))?"),
            TokenType.NUMBER_INTEGER,
        ),
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[bB][01_]+"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"0[oO][0-7_]+"), TokenType.NUMBER_OCT),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"->|=>|\?\?|\?\.|\.\.\.|\.\."), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<|>|!"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%|]"), TokenType.OPERATOR),
        # Assignment
        Rule(re.compile(r"="), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
