"""Regex lexer for Rosettes.

Thread-safe regex-based tokenizer for regular expression patterns.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["RegexLexer"]


class RegexLexer(PatternLexer):
    """Regular expression pattern lexer. Thread-safe."""

    name = "regex"
    aliases = ("regexp", "re")
    filenames = ()
    mimetypes = ()

    rules = (
        # Character classes
        Rule(re.compile(r"\\[dDwWsS]"), TokenType.NAME_BUILTIN),
        # Unicode categories: \p{L}, \P{Lu}
        Rule(re.compile(r"\\[pP]\{[^}]+\}"), TokenType.NAME_BUILTIN),
        # Escape sequences
        Rule(re.compile(r"\\[nrtfvae0]"), TokenType.STRING_ESCAPE),
        Rule(re.compile(r"\\x[0-9a-fA-F]{2}"), TokenType.STRING_ESCAPE),
        Rule(re.compile(r"\\u[0-9a-fA-F]{4}"), TokenType.STRING_ESCAPE),
        Rule(re.compile(r"\\U[0-9a-fA-F]{8}"), TokenType.STRING_ESCAPE),
        # Escaped special characters
        Rule(re.compile(r"\\[.*+?^${}()|\\[\]/-]"), TokenType.STRING_ESCAPE),
        # Backreferences: \1, \2, etc.
        Rule(re.compile(r"\\[1-9]\d*"), TokenType.NAME_VARIABLE),
        # Named backreferences: \k<name>
        Rule(re.compile(r"\\k<[^>]+>"), TokenType.NAME_VARIABLE),
        # Anchors
        Rule(re.compile(r"\\[bBAZz]|[\^$]"), TokenType.KEYWORD),
        # Character class brackets
        Rule(re.compile(r"\[\^?"), TokenType.PUNCTUATION),
        Rule(re.compile(r"\]"), TokenType.PUNCTUATION),
        # Character ranges in classes
        Rule(re.compile(r"[a-zA-Z0-9]-[a-zA-Z0-9]"), TokenType.STRING),
        # Grouping
        Rule(re.compile(r"\(\?:"), TokenType.PUNCTUATION),  # Non-capturing
        Rule(re.compile(r"\(\?="), TokenType.KEYWORD),  # Lookahead
        Rule(re.compile(r"\(\?!"), TokenType.KEYWORD),  # Negative lookahead
        Rule(re.compile(r"\(\?<="), TokenType.KEYWORD),  # Lookbehind
        Rule(re.compile(r"\(\?<!"), TokenType.KEYWORD),  # Negative lookbehind
        Rule(re.compile(r"\(\?>"), TokenType.KEYWORD),  # Atomic group
        Rule(re.compile(r"\(\?<[^>]+>"), TokenType.NAME_TAG),  # Named capture
        Rule(re.compile(r"\(\?P<[^>]+>"), TokenType.NAME_TAG),  # Python named capture
        Rule(re.compile(r"\(\?P=[^)]+\)"), TokenType.NAME_VARIABLE),  # Python named backref
        Rule(re.compile(r"\(\?[imsx-]+\)"), TokenType.KEYWORD),  # Flags
        Rule(re.compile(r"\(\?[imsx-]+:"), TokenType.KEYWORD),  # Flags with non-capture
        Rule(re.compile(r"[()]"), TokenType.PUNCTUATION),
        # Quantifiers
        Rule(re.compile(r"[*+?][\?+]?"), TokenType.OPERATOR),
        Rule(re.compile(r"\{\d+(?:,\d*)?\}[\?+]?"), TokenType.OPERATOR),
        # Alternation
        Rule(re.compile(r"\|"), TokenType.OPERATOR),
        # Wildcard
        Rule(re.compile(r"\."), TokenType.KEYWORD),
        # Literal characters
        Rule(re.compile(r"[a-zA-Z0-9_]+"), TokenType.STRING),
        # Other characters
        Rule(re.compile(r"[^\s\[\](){}|*+?.^$\\]+"), TokenType.STRING),
        # Whitespace (for verbose mode)
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
