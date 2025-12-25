"""Liquid template lexer for Rosettes.

Thread-safe regex-based tokenizer for Liquid template syntax (Jekyll, Shopify).
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["LiquidLexer"]

# Liquid keywords
_KEYWORDS = frozenset(
    (
        # Control flow
        "if",
        "elsif",
        "else",
        "endif",
        "unless",
        "endunless",
        "case",
        "when",
        "endcase",
        # Iteration
        "for",
        "endfor",
        "break",
        "continue",
        "cycle",
        "tablerow",
        "endtablerow",
        "limit",
        "offset",
        "reversed",
        # Variables
        "assign",
        "capture",
        "endcapture",
        "increment",
        "decrement",
        # Template
        "include",
        "render",
        "layout",
        "block",
        "endblock",
        "extends",
        "section",
        "endsection",
        "paginate",
        "endpaginate",
        # Comments
        "comment",
        "endcomment",
        # Raw
        "raw",
        "endraw",
        # Operators
        "and",
        "or",
        "not",
        "contains",
        "in",
        # Special
        "blank",
        "empty",
        "nil",
        "null",
        "true",
        "false",
        "forloop",
        "tablerowloop",
    )
)

# Liquid filters
_FILTERS = frozenset(
    (
        # String filters
        "append",
        "capitalize",
        "downcase",
        "escape",
        "escape_once",
        "lstrip",
        "newline_to_br",
        "prepend",
        "remove",
        "remove_first",
        "replace",
        "replace_first",
        "rstrip",
        "slice",
        "split",
        "strip",
        "strip_html",
        "strip_newlines",
        "truncate",
        "truncatewords",
        "upcase",
        "url_decode",
        "url_encode",
        # Math filters
        "abs",
        "at_least",
        "at_most",
        "ceil",
        "divided_by",
        "floor",
        "minus",
        "modulo",
        "plus",
        "round",
        "times",
        # Array filters
        "compact",
        "concat",
        "first",
        "join",
        "last",
        "map",
        "reverse",
        "size",
        "sort",
        "sort_natural",
        "uniq",
        "where",
        # Date filters
        "date",
        # Default
        "default",
        # JSON
        "json",
        # Jekyll-specific
        "relative_url",
        "absolute_url",
        "markdownify",
        "smartify",
        "slugify",
        "jsonify",
        "xml_escape",
        "cgi_escape",
        "uri_escape",
        "number_of_words",
        "group_by",
        "group_by_exp",
        "where_exp",
        "push",
        "pop",
        "shift",
        "unshift",
        "inspect",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify a word inside template tags."""
    word = match.group(0)
    if word in ("true", "false", "nil", "null", "blank", "empty"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("and", "or", "not", "contains", "in"):
        return TokenType.OPERATOR_WORD
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _FILTERS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class LiquidLexer(PatternLexer):
    """Liquid template lexer. Thread-safe."""

    name = "liquid"
    aliases = ("jekyll", "shopify-liquid")
    filenames = ("*.liquid",)
    mimetypes = ("text/x-liquid",)

    rules = (
        # Comments: {% comment %}...{% endcomment %}
        Rule(
            re.compile(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", re.DOTALL),
            TokenType.COMMENT_MULTILINE,
        ),
        # Raw blocks
        Rule(
            re.compile(r"\{%\s*raw\s*%\}.*?\{%\s*endraw\s*%\}", re.DOTALL),
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
        # Range: (1..5)
        Rule(re.compile(r"\.\."), TokenType.OPERATOR),
        # Brackets and parens
        Rule(re.compile(r"[\[\]():]"), TokenType.PUNCTUATION),
        # Keywords and identifiers
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"), _classify_word),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Plain text
        Rule(re.compile(r"[^\s{%}]+"), TokenType.TEXT),
    )
