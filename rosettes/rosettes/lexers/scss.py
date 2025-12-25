"""SCSS/Sass lexer for Rosettes.

Thread-safe regex-based tokenizer for SCSS and Sass CSS preprocessors.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["ScssLexer"]

# SCSS/CSS at-rules
_AT_RULES = frozenset(
    (
        "import",
        "media",
        "font-face",
        "keyframes",
        "supports",
        "charset",
        "namespace",
        "page",
        "document",
        "viewport",
        "counter-style",
        "font-feature-values",
        "property",
        "layer",
        "container",
        # Sass-specific
        "use",
        "forward",
        "mixin",
        "include",
        "function",
        "return",
        "extend",
        "error",
        "warn",
        "debug",
        "at-root",
        "if",
        "else",
        "each",
        "for",
        "while",
        "content",
    )
)


def _classify_at_rule(match: re.Match[str]) -> TokenType:
    """Classify @-rules."""
    return TokenType.KEYWORD


class ScssLexer(PatternLexer):
    """SCSS/Sass lexer. Thread-safe."""

    name = "scss"
    aliases = ("sass", "css-sass", "css-scss")
    filenames = ("*.scss", "*.sass")
    mimetypes = ("text/x-scss", "text/x-sass")

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*.*?\*/", re.DOTALL), TokenType.COMMENT_MULTILINE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Interpolation: #{...}
        Rule(re.compile(r"#\{[^}]+\}"), TokenType.STRING_INTERPOL),
        # Variables: $name
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_-]*"), TokenType.NAME_VARIABLE),
        # Placeholder selectors: %name
        Rule(re.compile(r"%[a-zA-Z_][a-zA-Z0-9_-]*"), TokenType.NAME_LABEL),
        # @-rules
        Rule(re.compile(r"@[a-zA-Z][a-zA-Z0-9-]*"), _classify_at_rule),
        # ID selectors: #name
        Rule(re.compile(r"#[a-zA-Z_][a-zA-Z0-9_-]*"), TokenType.NAME_ATTRIBUTE),
        # Class selectors: .name
        Rule(re.compile(r"\.[a-zA-Z_][a-zA-Z0-9_-]*"), TokenType.NAME_CLASS),
        # Pseudo-classes and pseudo-elements
        Rule(re.compile(r"::?[a-zA-Z][a-zA-Z0-9-]*"), TokenType.NAME_DECORATOR),
        # Colors: #fff, #ffffff
        Rule(re.compile(r"#[0-9a-fA-F]{3,8}\b"), TokenType.NUMBER_HEX),
        # Numbers with units
        Rule(
            re.compile(
                r"-?\d+\.?\d*(?:px|em|rem|%|vh|vw|vmin|vmax|ch|ex|cm|mm|in|pt|pc|deg|rad|turn|s|ms)?\b"
            ),
            TokenType.NUMBER,
        ),
        # URLs
        Rule(re.compile(r"url\([^)]+\)"), TokenType.STRING_OTHER),
        # Important
        Rule(re.compile(r"!important\b"), TokenType.KEYWORD),
        Rule(re.compile(r"!default\b"), TokenType.KEYWORD),
        Rule(re.compile(r"!global\b"), TokenType.KEYWORD),
        Rule(re.compile(r"!optional\b"), TokenType.KEYWORD),
        # Properties and identifiers
        Rule(re.compile(r"[a-zA-Z_][a-zA-Z0-9_-]*"), TokenType.NAME),
        # Operators
        Rule(re.compile(r"[+\-*/%]=?|[<>]=?|[=!]=|and|or|not"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[{}();:,\[\]&>~+]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
