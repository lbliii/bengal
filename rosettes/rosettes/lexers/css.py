"""CSS lexer for Rosettes.

Thread-safe regex-based tokenizer for CSS stylesheets.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["CssLexer"]


class CssLexer(PatternLexer):
    """CSS lexer.

    Handles CSS3 syntax including selectors, properties, values, and at-rules.
    Thread-safe: all state is immutable.
    """

    name = "css"
    aliases = ()
    filenames = ("*.css",)
    mimetypes = ("text/css",)

    rules = (
        # Comments
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # At-rules
        Rule(re.compile(r"@[a-zA-Z-]+"), TokenType.KEYWORD),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING),
        # URLs
        Rule(re.compile(r"url\([^)]+\)"), TokenType.STRING_OTHER),
        # Hex colors
        Rule(re.compile(r"#[0-9a-fA-F]{3,8}\b"), TokenType.NUMBER_HEX),
        # Numbers with units
        Rule(
            re.compile(
                r"-?(?:\d+\.\d+|\.\d+|\d+)(?:em|ex|ch|rem|vw|vh|vmin|vmax|cm|mm|in|px|pt|pc|%|s|ms|deg|rad|turn)?"
            ),
            TokenType.NUMBER,
        ),
        # Important
        Rule(re.compile(r"!important\b"), TokenType.KEYWORD_PSEUDO),
        # Pseudo-classes and pseudo-elements
        Rule(re.compile(r"::?[a-zA-Z-]+(?:\([^)]*\))?"), TokenType.KEYWORD_PSEUDO),
        # ID selectors
        Rule(re.compile(r"#[a-zA-Z_-][a-zA-Z0-9_-]*"), TokenType.NAME_VARIABLE),
        # Class selectors
        Rule(re.compile(r"\.[a-zA-Z_-][a-zA-Z0-9_-]*"), TokenType.NAME_CLASS),
        # Element selectors
        Rule(re.compile(r"[a-zA-Z][a-zA-Z0-9-]*"), TokenType.NAME_TAG),
        # Property names (followed by colon)
        Rule(re.compile(r"[a-zA-Z-]+(?=\s*:)"), TokenType.NAME_ATTRIBUTE),
        # Values (keywords)
        Rule(re.compile(r"[a-zA-Z-]+"), TokenType.NAME),
        # Operators
        Rule(re.compile(r"[~*^$|]?="), TokenType.OPERATOR),
        Rule(re.compile(r"[>+~]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[{}();:,\[\]]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
