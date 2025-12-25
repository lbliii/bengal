"""Handlebars/Mustache lexer for Rosettes.

Thread-safe regex-based tokenizer for Handlebars and Mustache templates.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["HandlebarsLexer"]

# Handlebars keywords
_KEYWORDS = frozenset(
    (
        "if",
        "else",
        "unless",
        "each",
        "with",
        "lookup",
        "log",
        "blockHelperMissing",
        "helperMissing",
        "this",
    )
)

# Built-in helpers
_HELPERS = frozenset(
    (
        "if",
        "unless",
        "each",
        "with",
        "lookup",
        "log",
        "helperMissing",
        "blockHelperMissing",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify Handlebars identifiers."""
    word = match.group(0)
    if word in ("true", "false", "null", "undefined"):
        return TokenType.KEYWORD_CONSTANT
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _HELPERS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class HandlebarsLexer(PatternLexer):
    """Handlebars/Mustache lexer. Thread-safe."""

    name = "handlebars"
    aliases = ("hbs", "mustache", "htmlbars")
    filenames = ("*.hbs", "*.handlebars", "*.mustache")
    mimetypes = ("text/x-handlebars-template",)

    rules = (
        # Comments: {{!-- comment --}} or {{! comment }}
        Rule(re.compile(r"\{\{!--.*?--\}\}", re.DOTALL), TokenType.COMMENT_MULTILINE),
        Rule(re.compile(r"\{\{!.*?\}\}"), TokenType.COMMENT_SINGLE),
        # Raw blocks: {{{{raw}}}} ... {{{{/raw}}}}
        Rule(re.compile(r"\{\{\{\{[^}]+\}\}\}\}"), TokenType.KEYWORD),
        # Triple-stash (unescaped): {{{expression}}}
        Rule(re.compile(r"\{\{\{"), TokenType.PUNCTUATION),
        Rule(re.compile(r"\}\}\}"), TokenType.PUNCTUATION),
        # Block helpers: {{#helper}} {{/helper}}
        Rule(re.compile(r"\{\{#"), TokenType.PUNCTUATION),
        Rule(re.compile(r"\{\{/"), TokenType.PUNCTUATION),
        # Partials: {{> partial}}
        Rule(re.compile(r"\{\{>"), TokenType.PUNCTUATION),
        # Else: {{else}} or {{^}}
        Rule(re.compile(r"\{\{\^"), TokenType.PUNCTUATION),
        # Regular expressions: {{ }}
        Rule(re.compile(r"\{\{"), TokenType.PUNCTUATION),
        Rule(re.compile(r"\}\}"), TokenType.PUNCTUATION),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Numbers
        Rule(re.compile(r"-?\d+\.\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d+"), TokenType.NUMBER_INTEGER),
        # Path segments: this, @index, @key, @first, @last
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_BUILTIN_PSEUDO),
        Rule(re.compile(r"\.\."), TokenType.OPERATOR),  # Parent context
        Rule(re.compile(r"\."), TokenType.PUNCTUATION),  # Property access
        # Hash parameters: key=value
        Rule(re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*(?==)"), TokenType.NAME_ATTRIBUTE),
        # Operators
        Rule(re.compile(r"="), TokenType.OPERATOR),
        # Keywords and identifiers
        Rule(re.compile(r"[a-zA-Z_][a-zA-Z0-9_-]*"), _classify_word),
        # Brackets
        Rule(re.compile(r"[\[\]()]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Plain text
        Rule(re.compile(r"[^\s{}]+"), TokenType.TEXT),
    )
