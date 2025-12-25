"""Java lexer for Rosettes.

Thread-safe regex-based tokenizer for Java source code.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["JavaLexer"]

_KEYWORDS = (
    "abstract",
    "assert",
    "break",
    "case",
    "catch",
    "class",
    "const",
    "continue",
    "default",
    "do",
    "else",
    "enum",
    "extends",
    "final",
    "finally",
    "for",
    "goto",
    "if",
    "implements",
    "import",
    "instanceof",
    "interface",
    "native",
    "new",
    "package",
    "private",
    "protected",
    "public",
    "return",
    "static",
    "strictfp",
    "super",
    "switch",
    "synchronized",
    "this",
    "throw",
    "throws",
    "transient",
    "try",
    "volatile",
    "while",
    "yield",
    # Java 10+
    "var",
    "record",
    "sealed",
    "non-sealed",
    "permits",
)

_TYPES = (
    "boolean",
    "byte",
    "char",
    "double",
    "float",
    "int",
    "long",
    "short",
    "void",
    "String",
    "Object",
    "Class",
    "Integer",
    "Long",
    "Double",
    "Float",
    "Boolean",
    "Character",
    "Byte",
    "Short",
    "Void",
    "List",
    "Map",
    "Set",
    "Collection",
    "ArrayList",
    "HashMap",
    "HashSet",
    "Optional",
    "Stream",
)

_CONSTANTS = ("true", "false", "null")


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in ("class", "interface", "enum", "record", "extends", "implements"):
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


class JavaLexer(PatternLexer):
    """Java lexer. Thread-safe."""

    name = "java"
    aliases = ()
    filenames = ("*.java",)
    mimetypes = ("text/x-java",)

    _WORD_PATTERN = r"\b[a-zA-Z_$][a-zA-Z0-9_$]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*\*[\s\S]*?\*/"), TokenType.STRING_DOC),  # Javadoc
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Annotations
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_DECORATOR),
        # Text blocks (Java 15+)
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING_DOC),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Characters
        Rule(re.compile(r"'[^'\\]'|'\\.'|'\\u[0-9a-fA-F]{4}'"), TokenType.STRING_CHAR),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+[lL]?"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[bB][01_]+[lL]?"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"0[0-7_]+[lL]?"), TokenType.NUMBER_OCT),
        Rule(
            re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?[fFdD]?"), TokenType.NUMBER_FLOAT
        ),
        Rule(re.compile(r"\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?[fFdD]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?\d[\d_]*[fFdD]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[lLfFdD]?"), TokenType.NUMBER_INTEGER),
        # Keywords/types/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Lambda
        Rule(re.compile(r"->"), TokenType.OPERATOR),
        # Operators
        Rule(re.compile(r"\+\+|--"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<<|>>>|>>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|>>>="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!~<>=?:]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
