"""Awk lexer for Rosettes.

Thread-safe regex-based tokenizer for Awk scripts.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["AwkLexer"]

# Awk keywords
_KEYWORDS = frozenset(
    (
        "BEGIN",
        "END",
        "BEGINFILE",
        "ENDFILE",
        "if",
        "else",
        "while",
        "do",
        "for",
        "in",
        "break",
        "continue",
        "delete",
        "exit",
        "next",
        "nextfile",
        "return",
        "function",
        "getline",
        "print",
        "printf",
        "switch",
        "case",
        "default",
    )
)

# Built-in functions
_BUILTINS = frozenset(
    (
        # String functions
        "gsub",
        "index",
        "length",
        "match",
        "split",
        "sprintf",
        "sub",
        "substr",
        "tolower",
        "toupper",
        "gensub",
        "patsplit",
        "strftime",
        "systime",
        "mktime",
        # Numeric functions
        "atan2",
        "cos",
        "exp",
        "int",
        "log",
        "rand",
        "sin",
        "sqrt",
        "srand",
        # I/O functions
        "close",
        "fflush",
        "system",
        # Misc
        "and",
        "compl",
        "lshift",
        "or",
        "rshift",
        "xor",
        "isarray",
        "typeof",
    )
)

# Built-in variables
_BUILTIN_VARS = frozenset(
    (
        "ARGC",
        "ARGV",
        "CONVFMT",
        "ENVIRON",
        "FILENAME",
        "FNR",
        "FS",
        "NF",
        "NR",
        "OFMT",
        "OFS",
        "ORS",
        "RLENGTH",
        "RS",
        "RSTART",
        "SUBSEP",
        # gawk extensions
        "BINMODE",
        "FIELDWIDTHS",
        "FPAT",
        "IGNORECASE",
        "LINT",
        "PREC",
        "ROUNDMODE",
        "TEXTDOMAIN",
        "PROCINFO",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify Awk identifiers."""
    word = match.group(0)
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    if word in _BUILTIN_VARS:
        return TokenType.NAME_BUILTIN_PSEUDO
    return TokenType.NAME


class AwkLexer(PatternLexer):
    """Awk lexer. Thread-safe."""

    name = "awk"
    aliases = ("gawk", "mawk", "nawk")
    filenames = ("*.awk",)
    mimetypes = ("application/x-awk", "text/x-awk")

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        # Regex patterns: /pattern/ or /pattern/flags
        Rule(re.compile(r"/(?:[^/\\]|\\.)+/[gimsux]*"), TokenType.STRING_REGEX),
        # Field references: $0, $1, $NF, $(expr)
        Rule(re.compile(r"\$\d+"), TokenType.NAME_VARIABLE),
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),
        Rule(re.compile(r"\$\("), TokenType.NAME_VARIABLE),
        # Numbers
        Rule(re.compile(r"-?\d+\.\d+(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d+[eE][+-]?\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"0[xX][0-9a-fA-F]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"-?\d+"), TokenType.NUMBER_INTEGER),
        # Operators
        Rule(re.compile(r"\+\+|--|&&|\|\||!~|~|[<>!=]=?|[+\-*/%^]=?"), TokenType.OPERATOR),
        Rule(re.compile(r"\?|:"), TokenType.OPERATOR),
        # Keywords and identifiers
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"), _classify_word),
        # Punctuation
        Rule(re.compile(r"[{}()\[\];,]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
