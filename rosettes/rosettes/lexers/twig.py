"""Twig template lexer for Rosettes.

Thread-safe regex-based tokenizer for Twig templates (Symfony, Drupal).
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["TwigLexer"]

# Twig keywords
_KEYWORDS = frozenset(
    (
        # Tags
        "autoescape",
        "endautoescape",
        "block",
        "endblock",
        "cache",
        "endcache",
        "deprecated",
        "do",
        "embed",
        "endembed",
        "extends",
        "flush",
        "for",
        "endfor",
        "from",
        "if",
        "elseif",
        "else",
        "endif",
        "import",
        "include",
        "macro",
        "endmacro",
        "sandbox",
        "endsandbox",
        "set",
        "endset",
        "use",
        "verbatim",
        "endverbatim",
        "with",
        "endwith",
        "apply",
        "endapply",
        # Operators
        "and",
        "or",
        "not",
        "in",
        "is",
        "as",
        "b-and",
        "b-or",
        "b-xor",
        "starts",
        "ends",
        "matches",
        # Special
        "true",
        "false",
        "null",
        "none",
        "loop",
        "_self",
        "varargs",
        "only",
        "ignore",
        "missing",
    )
)

# Twig filters
_FILTERS = frozenset(
    (
        "abs",
        "batch",
        "capitalize",
        "column",
        "convert_encoding",
        "country_name",
        "currency_name",
        "currency_symbol",
        "data_uri",
        "date",
        "date_modify",
        "default",
        "e",
        "escape",
        "filter",
        "first",
        "format",
        "format_currency",
        "format_date",
        "format_datetime",
        "format_number",
        "format_time",
        "html_to_markdown",
        "inky_to_html",
        "inline_css",
        "join",
        "json_encode",
        "keys",
        "language_name",
        "last",
        "length",
        "locale_name",
        "lower",
        "map",
        "markdown_to_html",
        "merge",
        "nl2br",
        "number_format",
        "raw",
        "reduce",
        "replace",
        "reverse",
        "round",
        "slice",
        "slug",
        "sort",
        "spaceless",
        "split",
        "striptags",
        "timezone_name",
        "title",
        "trim",
        "u",
        "upper",
        "url_encode",
    )
)

# Twig tests
_TESTS = frozenset(
    (
        "constant",
        "defined",
        "divisible",
        "empty",
        "even",
        "iterable",
        "null",
        "odd",
        "same",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify Twig identifiers."""
    word = match.group(0)
    if word in ("true", "false", "null", "none"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("and", "or", "not", "in", "is"):
        return TokenType.OPERATOR_WORD
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _FILTERS:
        return TokenType.NAME_BUILTIN
    if word in _TESTS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class TwigLexer(PatternLexer):
    """Twig template lexer. Thread-safe."""

    name = "twig"
    aliases = ("symfony", "drupal-twig")
    filenames = ("*.twig", "*.html.twig")
    mimetypes = ("text/x-twig",)

    rules = (
        # Comments: {# ... #}
        Rule(re.compile(r"\{#.*?#\}", re.DOTALL), TokenType.COMMENT_MULTILINE),
        # Verbatim blocks
        Rule(
            re.compile(r"\{%\s*verbatim\s*%\}.*?\{%\s*endverbatim\s*%\}", re.DOTALL),
            TokenType.STRING_OTHER,
        ),
        # Tag delimiters: {% ... %}
        Rule(re.compile(r"\{%-?"), TokenType.PUNCTUATION),
        Rule(re.compile(r"-?%\}"), TokenType.PUNCTUATION),
        # Output delimiters: {{ ... }}
        Rule(re.compile(r"\{\{-?"), TokenType.PUNCTUATION),
        Rule(re.compile(r"-?\}\}"), TokenType.PUNCTUATION),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Numbers
        Rule(re.compile(r"-?\d+\.\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d+"), TokenType.NUMBER_INTEGER),
        # Filter operator
        Rule(re.compile(r"\|"), TokenType.OPERATOR),
        # Range: ..
        Rule(re.compile(r"\.\."), TokenType.OPERATOR),
        # Dot notation
        Rule(re.compile(r"\."), TokenType.PUNCTUATION),
        # Comparison operators
        Rule(re.compile(r"==|!=|<=|>=|<>|<|>|~"), TokenType.OPERATOR),
        # Ternary
        Rule(re.compile(r"\?:?|:"), TokenType.OPERATOR),
        # Null coalescing
        Rule(re.compile(r"\?\?"), TokenType.OPERATOR),
        # Arrow function
        Rule(re.compile(r"=>"), TokenType.OPERATOR),
        # Brackets and parens
        Rule(re.compile(r"[\[\](){}]"), TokenType.PUNCTUATION),
        # Keywords and identifiers
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"), _classify_word),
        # Comma
        Rule(re.compile(r","), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Plain text
        Rule(re.compile(r"[^\s{%}]+"), TokenType.TEXT),
    )
