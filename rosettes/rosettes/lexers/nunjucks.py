"""Nunjucks lexer for Rosettes.

Thread-safe regex-based tokenizer for Nunjucks templates (Mozilla, Eleventy).
Very similar to Jinja2 but with some differences.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["NunjucksLexer"]

# Nunjucks keywords
_KEYWORDS = frozenset(
    (
        # Control flow
        "if",
        "elif",
        "elseif",
        "else",
        "endif",
        "for",
        "endfor",
        "asyncEach",
        "endeach",
        "asyncAll",
        "endall",
        # Blocks
        "block",
        "endblock",
        "extends",
        "include",
        "import",
        "from",
        "as",
        # Macros
        "macro",
        "endmacro",
        "call",
        "endcall",
        # Variables
        "set",
        "endset",
        # Filters
        "filter",
        "endfilter",
        # Raw
        "raw",
        "endraw",
        "verbatim",
        "endverbatim",
        # Operators
        "and",
        "or",
        "not",
        "in",
        "is",
        # Special
        "true",
        "false",
        "none",
        "null",
        "loop",
        "super",
        "caller",
    )
)

# Nunjucks filters
_FILTERS = frozenset(
    (
        "abs",
        "batch",
        "capitalize",
        "center",
        "default",
        "d",
        "dictsort",
        "dump",
        "escape",
        "e",
        "first",
        "float",
        "forceescape",
        "groupby",
        "indent",
        "int",
        "join",
        "last",
        "length",
        "list",
        "lower",
        "nl2br",
        "random",
        "reject",
        "rejectattr",
        "replace",
        "reverse",
        "round",
        "safe",
        "select",
        "selectattr",
        "slice",
        "sort",
        "string",
        "striptags",
        "sum",
        "title",
        "trim",
        "truncate",
        "upper",
        "urlencode",
        "urlize",
        "wordcount",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify Nunjucks identifiers."""
    word = match.group(0)
    if word in ("true", "false", "none", "null"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("and", "or", "not", "in", "is"):
        return TokenType.OPERATOR_WORD
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _FILTERS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class NunjucksLexer(PatternLexer):
    """Nunjucks template lexer. Thread-safe."""

    name = "nunjucks"
    aliases = ("njk", "11ty", "eleventy")
    filenames = ("*.njk", "*.nunjucks")
    mimetypes = ("text/x-nunjucks",)

    rules = (
        # Comments: {# ... #}
        Rule(re.compile(r"\{#.*?#\}", re.DOTALL), TokenType.COMMENT_MULTILINE),
        # Raw blocks
        Rule(
            re.compile(r"\{%\s*raw\s*%\}.*?\{%\s*endraw\s*%\}", re.DOTALL),
            TokenType.STRING_OTHER,
        ),
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
        # Dot notation
        Rule(re.compile(r"\."), TokenType.PUNCTUATION),
        # Comparison operators
        Rule(re.compile(r"==|!=|<=|>=|<>|<|>|="), TokenType.OPERATOR),
        # Brackets and parens
        Rule(re.compile(r"[\[\]():]"), TokenType.PUNCTUATION),
        # Keywords and identifiers
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"), _classify_word),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Plain text
        Rule(re.compile(r"[^\s{%}]+"), TokenType.TEXT),
    )
