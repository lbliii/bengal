"""Groovy lexer for Rosettes.

Thread-safe regex-based tokenizer for Groovy source code.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["GroovyLexer"]

_KEYWORDS = (
    "abstract",
    "as",
    "assert",
    "break",
    "case",
    "catch",
    "class",
    "const",
    "continue",
    "def",
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
    "in",
    "instanceof",
    "interface",
    "native",
    "new",
    "non-sealed",
    "package",
    "permits",
    "private",
    "protected",
    "public",
    "record",
    "return",
    "sealed",
    "static",
    "strictfp",
    "super",
    "switch",
    "synchronized",
    "this",
    "throw",
    "throws",
    "trait",
    "transient",
    "try",
    "var",
    "volatile",
    "while",
    "with",
    "yield",
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
    "Boolean",
    "Byte",
    "Character",
    "Double",
    "Float",
    "Integer",
    "Long",
    "Short",
    "String",
    "Object",
    "List",
    "Map",
    "Set",
    "Closure",
)

_CONSTANTS = ("true", "false", "null")


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in ("class", "interface", "enum", "trait", "def", "var", "record"):
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


class GroovyLexer(PatternLexer):
    """Groovy lexer. Thread-safe."""

    name = "groovy"
    aliases = ("gradle",)
    filenames = ("*.groovy", "*.gradle", "Jenkinsfile")
    mimetypes = ("text/x-groovy",)

    _WORD_PATTERN = r"\b[a-zA-Z_$][a-zA-Z0-9_$]*\b"

    rules = (
        # Shebang
        Rule(re.compile(r"^#!.*$", re.MULTILINE), TokenType.COMMENT_HASHBANG),
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*\*[\s\S]*?\*/"), TokenType.STRING_DOC),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Annotations
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_DECORATOR),
        # Triple-quoted strings (GStrings)
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING),
        Rule(re.compile(r"'''[\s\S]*?'''"), TokenType.STRING),
        # Slashy strings (regex)
        Rule(re.compile(r"~/[^/\n]*(?:\\.[^/\n]*)*/"), TokenType.STRING_REGEX),
        Rule(re.compile(r"/[^/\n]*(?:\\.[^/\n]*)*/"), TokenType.STRING_REGEX),
        # Dollar slashy strings
        Rule(re.compile(r"\$/[\s\S]*?/\$"), TokenType.STRING),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+[gGlL]?"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[bB][01_]+[gGlL]?"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"0[0-7_]+[gGlL]?"), TokenType.NUMBER_OCT),
        Rule(
            re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?[fFdDgG]?"), TokenType.NUMBER_FLOAT
        ),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?\d[\d_]*[fFdDgG]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[gGlLfFdD]?"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Safe navigation and spread operators
        Rule(re.compile(r"\?\.|\.&|\*\.|\.@|<=>|<>|=~|==~"), TokenType.OPERATOR),
        # Operators
        Rule(re.compile(r"->|\.\.<?"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<<|>>>|>>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|>>>=|\*\*="), TokenType.OPERATOR),
        Rule(re.compile(r"\+\+|--|\*\*"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!~<>=?:]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
