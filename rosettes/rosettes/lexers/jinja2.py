"""Jinja2 template lexer for Rosettes.

Thread-safe regex-based tokenizer for Jinja2 template syntax.
Highlights template tags, expressions, filters, and control structures.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["Jinja2Lexer"]

# Jinja2 statement keywords
_KEYWORDS = frozenset(
    (
        # Control flow
        "if",
        "elif",
        "else",
        "endif",
        "for",
        "endfor",
        "while",
        "endwhile",
        # Blocks and inheritance
        "block",
        "endblock",
        "extends",
        "include",
        "import",
        "from",
        "as",
        "with",
        "endwith",
        "without",
        "context",
        # Macros
        "macro",
        "endmacro",
        "call",
        "endcall",
        # Variables
        "set",
        "endset",
        "do",
        # Filters and tests
        "filter",
        "endfilter",
        # Raw/escape
        "raw",
        "endraw",
        "autoescape",
        "endautoescape",
        # Debugging
        "debug",
        # Scoping
        "scoped",
        "required",
        # Boolean operators
        "and",
        "or",
        "not",
        "in",
        "is",
        # Comparison
        "true",
        "false",
        "none",
        "True",
        "False",
        "None",
        # Misc
        "recursive",
        "ignore",
        "missing",
        "pluralize",
        "trans",
        "endtrans",
        "continue",
        "break",
    )
)

# Common Jinja2 filters
_FILTERS = frozenset(
    (
        # String filters
        "capitalize",
        "center",
        "escape",
        "e",
        "forceescape",
        "format",
        "indent",
        "lower",
        "replace",
        "safe",
        "striptags",
        "title",
        "trim",
        "truncate",
        "upper",
        "urlencode",
        "urlize",
        "wordcount",
        "wordwrap",
        # List filters
        "batch",
        "first",
        "groupby",
        "items",
        "join",
        "last",
        "length",
        "list",
        "map",
        "max",
        "min",
        "random",
        "reject",
        "rejectattr",
        "reverse",
        "select",
        "selectattr",
        "slice",
        "sort",
        "sum",
        "unique",
        # Type filters
        "abs",
        "attr",
        "default",
        "d",
        "dictsort",
        "filesizeformat",
        "float",
        "int",
        "pprint",
        "round",
        "string",
        "tojson",
        "xmlattr",
    )
)

# Common Jinja2 tests
_TESTS = frozenset(
    (
        "callable",
        "defined",
        "divisibleby",
        "eq",
        "equalto",
        "escaped",
        "even",
        "ge",
        "gt",
        "in",
        "iterable",
        "le",
        "lower",
        "lt",
        "mapping",
        "ne",
        "none",
        "number",
        "odd",
        "sameas",
        "sequence",
        "string",
        "undefined",
        "upper",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify a word inside template tags."""
    word = match.group(0)
    if word in ("true", "false", "none", "True", "False", "None"):
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


class Jinja2Lexer(PatternLexer):
    """Jinja2 template lexer. Thread-safe.

    Highlights Jinja2 template syntax:
        - Comments: {# comment #}
        - Expressions: {{ variable }}, {{ value | filter }}
        - Statements: {% if condition %}, {% for item in list %}
        - Filters: | filter_name
        - Variables and attributes
    """

    name = "jinja2"
    aliases = ("jinja", "j2", "jinja2-html", "html+jinja", "htmldjango")
    filenames = ("*.j2", "*.jinja", "*.jinja2", "*.html.j2")
    mimetypes = ("application/x-jinja", "text/x-jinja")

    rules = (
        # Comments: {# ... #}
        Rule(re.compile(r"\{#.*?#\}", re.DOTALL), TokenType.COMMENT_MULTILINE),
        # Raw blocks (don't highlight content)
        Rule(
            re.compile(r"\{%\s*raw\s*%\}.*?\{%\s*endraw\s*%\}", re.DOTALL),
            TokenType.STRING_OTHER,
        ),
        # Statement tags: {% ... %}
        Rule(re.compile(r"\{%-?"), TokenType.PUNCTUATION),
        Rule(re.compile(r"-?%\}"), TokenType.PUNCTUATION),
        # Expression tags: {{ ... }}
        Rule(re.compile(r"\{\{-?"), TokenType.PUNCTUATION),
        Rule(re.compile(r"-?\}\}"), TokenType.PUNCTUATION),
        # Strings inside templates
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Numbers
        Rule(re.compile(r"\d+\.\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+"), TokenType.NUMBER_INTEGER),
        # Filter operator
        Rule(re.compile(r"\|"), TokenType.OPERATOR),
        # Attribute access
        Rule(re.compile(r"\."), TokenType.PUNCTUATION),
        # Comparison and assignment
        Rule(re.compile(r"==|!=|<=|>=|<|>|="), TokenType.OPERATOR),
        # Arithmetic
        Rule(re.compile(r"[+\-*/%~]"), TokenType.OPERATOR),
        # Parentheses, brackets, etc.
        Rule(re.compile(r"[\[\](){}:,]"), TokenType.PUNCTUATION),
        # Keywords and identifiers
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"), _classify_word),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
        # Anything else (plain text between template tags)
        Rule(re.compile(r"[^\s{%#}]+"), TokenType.TEXT),
    )
