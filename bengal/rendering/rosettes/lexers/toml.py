"""TOML lexer for Rosettes.

Thread-safe regex-based tokenizer for TOML configuration files.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["TomlLexer"]


class TomlLexer(PatternLexer):
    """TOML lexer.

    Handles TOML 1.0 syntax including inline tables, arrays, and datetime.
    Thread-safe: all state is immutable.
    """

    name = "toml"
    aliases = ()
    filenames = ("*.toml",)
    mimetypes = ("application/toml",)

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Table headers
        Rule(re.compile(r"\[\[[\w.-]+\]\]"), TokenType.NAME_CLASS),  # Array of tables
        Rule(re.compile(r"\[[\w.-]+\]"), TokenType.NAME_CLASS),  # Table
        # Keys (bare and dotted)
        Rule(re.compile(r"[a-zA-Z_][a-zA-Z0-9_-]*(?=\s*=)"), TokenType.NAME_ATTRIBUTE),
        # Multi-line strings (before single-line)
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING_DOC),
        Rule(re.compile(r"'''[\s\S]*?'''"), TokenType.STRING_DOC),
        # Literal strings
        Rule(re.compile(r"'[^'\n]*'"), TokenType.STRING_SINGLE),
        # Basic strings
        Rule(re.compile(r'"[^"\\\n]*(?:\\.[^"\\\n]*)*"'), TokenType.STRING),
        # DateTime (must be before numbers)
        Rule(
            re.compile(
                r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?"
            ),
            TokenType.LITERAL_DATE,
        ),
        # Time only
        Rule(re.compile(r"\d{2}:\d{2}:\d{2}(?:\.\d+)?"), TokenType.LITERAL_DATE),
        # Numbers
        Rule(re.compile(r"0x[0-9a-fA-F_]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0o[0-7_]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"0b[01_]+"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"[+-]?(?:inf|nan)"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"[+-]?\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"[+-]?\d[\d_]*[eE][+-]?\d[\d_]*"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"[+-]?\d[\d_]*"), TokenType.NUMBER_INTEGER),
        # Boolean
        Rule(re.compile(r"\b(?:true|false)\b"), TokenType.KEYWORD_CONSTANT),
        # Punctuation
        Rule(re.compile(r"[=,{}\[\]]"), TokenType.PUNCTUATION),
        Rule(re.compile(r"\."), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
