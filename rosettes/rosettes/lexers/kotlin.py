"""Kotlin lexer for Rosettes.

Thread-safe regex-based tokenizer for Kotlin source code.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["KotlinLexer"]

_KEYWORDS = (
    "abstract",
    "actual",
    "annotation",
    "as",
    "break",
    "by",
    "catch",
    "class",
    "companion",
    "const",
    "constructor",
    "continue",
    "crossinline",
    "data",
    "delegate",
    "do",
    "dynamic",
    "else",
    "enum",
    "expect",
    "external",
    "field",
    "file",
    "final",
    "finally",
    "for",
    "fun",
    "get",
    "if",
    "import",
    "in",
    "infix",
    "init",
    "inline",
    "inner",
    "interface",
    "internal",
    "is",
    "it",
    "lateinit",
    "noinline",
    "object",
    "open",
    "operator",
    "out",
    "override",
    "package",
    "param",
    "private",
    "property",
    "protected",
    "public",
    "receiver",
    "reified",
    "return",
    "sealed",
    "set",
    "setparam",
    "super",
    "suspend",
    "tailrec",
    "this",
    "throw",
    "try",
    "typealias",
    "typeof",
    "val",
    "value",
    "var",
    "vararg",
    "when",
    "where",
    "while",
)

_TYPES = (
    "Any",
    "Boolean",
    "Byte",
    "Char",
    "Double",
    "Float",
    "Int",
    "Long",
    "Nothing",
    "Short",
    "String",
    "Unit",
    "Array",
    "List",
    "Map",
    "Set",
    "MutableList",
    "MutableMap",
    "MutableSet",
    "Pair",
    "Triple",
    "Sequence",
)

_CONSTANTS = ("true", "false", "null")


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in ("class", "interface", "object", "enum", "fun", "val", "var", "typealias"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "package"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class KotlinLexer(PatternLexer):
    """Kotlin lexer. Thread-safe."""

    name = "kotlin"
    aliases = ("kt", "kts")
    filenames = ("*.kt", "*.kts")
    mimetypes = ("text/x-kotlin",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*\*[\s\S]*?\*/"), TokenType.STRING_DOC),  # KDoc
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Annotations
        Rule(
            re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*"),
            TokenType.NAME_DECORATOR,
        ),
        # Raw strings
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING_DOC),
        # Strings with interpolation
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Characters
        Rule(re.compile(r"'[^'\\]'|'\\.'|'\\u[0-9a-fA-F]{4}'"), TokenType.STRING_CHAR),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+[uUL]*"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[bB][01_]+[uUL]*"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?[fF]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?\d[\d_]*[fF]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[uUL]*"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"->|\.\.|\?\.|::|\?:"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|===|!==|<=|>=|<|>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%="), TokenType.OPERATOR),
        Rule(re.compile(r"\+\+|--"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!~<>=?:]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
