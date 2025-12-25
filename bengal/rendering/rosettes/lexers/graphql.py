"""GraphQL lexer for Rosettes.

Thread-safe regex-based tokenizer for GraphQL queries and schemas.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["GraphQLLexer"]

_KEYWORDS = (
    "directive",
    "enum",
    "extend",
    "fragment",
    "implements",
    "input",
    "interface",
    "mutation",
    "on",
    "query",
    "scalar",
    "schema",
    "subscription",
    "type",
    "union",
)

_TYPES = (
    "Boolean",
    "Float",
    "ID",
    "Int",
    "String",
)

_CONSTANTS = ("true", "false", "null")


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in ("type", "interface", "enum", "input", "union", "scalar", "fragment"):
        return TokenType.KEYWORD_DECLARATION
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class GraphQLLexer(PatternLexer):
    """GraphQL lexer. Thread-safe."""

    name = "graphql"
    aliases = ("gql",)
    filenames = ("*.graphql", "*.gql")
    mimetypes = ("application/graphql",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Description strings (triple-quoted)
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING_DOC),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Directives
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_DECORATOR),
        # Variables
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),
        # Numbers
        Rule(re.compile(r"-?\d+\.\d+(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d+(?:[eE][+-]?\d+)?"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Type modifiers
        Rule(re.compile(r"!"), TokenType.OPERATOR),
        # Spread operator
        Rule(re.compile(r"\.\.\."), TokenType.OPERATOR),
        # Assignment
        Rule(re.compile(r"[=:]"), TokenType.OPERATOR),
        # Logical operators (for filters)
        Rule(re.compile(r"&&|\|\|"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}|,]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
