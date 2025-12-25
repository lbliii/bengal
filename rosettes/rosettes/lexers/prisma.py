"""Prisma schema lexer for Rosettes.

Thread-safe regex-based tokenizer for Prisma database schemas.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["PrismaLexer"]

# Prisma keywords
_KEYWORDS = frozenset(
    (
        "datasource",
        "generator",
        "model",
        "enum",
        "type",
        "view",
    )
)

# Prisma field types
_TYPES = frozenset(
    (
        "String",
        "Boolean",
        "Int",
        "BigInt",
        "Float",
        "Decimal",
        "DateTime",
        "Json",
        "Bytes",
        "Unsupported",
    )
)

# Prisma attributes
_ATTRIBUTES = frozenset(
    (
        "@id",
        "@unique",
        "@default",
        "@relation",
        "@map",
        "@updatedAt",
        "@ignore",
        "@@id",
        "@@unique",
        "@@index",
        "@@map",
        "@@ignore",
        "@@fulltext",
        "@@schema",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify Prisma identifiers."""
    word = match.group(0)
    if word in ("true", "false", "null"):
        return TokenType.KEYWORD_CONSTANT
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    # Relation names (typically PascalCase)
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class PrismaLexer(PatternLexer):
    """Prisma schema lexer. Thread-safe."""

    name = "prisma"
    aliases = ()
    filenames = ("*.prisma",)
    mimetypes = ("text/x-prisma",)

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"///.*$", re.MULTILINE), TokenType.STRING_DOC),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        # Attributes: @attribute, @@attribute
        Rule(re.compile(r"@@?[a-zA-Z][a-zA-Z0-9_]*"), TokenType.NAME_DECORATOR),
        # Field modifiers: ?, []
        Rule(re.compile(r"\?"), TokenType.OPERATOR),
        Rule(re.compile(r"\[\]"), TokenType.OPERATOR),
        # Numbers
        Rule(re.compile(r"-?\d+\.\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d+"), TokenType.NUMBER_INTEGER),
        # Functions in attributes: autoincrement(), now(), uuid()
        Rule(re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*(?=\()"), TokenType.NAME_FUNCTION),
        # Keywords and identifiers
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"), _classify_word),
        # Punctuation
        Rule(re.compile(r"[{}()\[\]:,=]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
