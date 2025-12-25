"""INI/Properties lexer for Rosettes.

Thread-safe regex-based tokenizer for INI-style configuration files.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["IniLexer"]


class IniLexer(PatternLexer):
    """INI/Properties lexer. Thread-safe."""

    name = "ini"
    aliases = ("cfg", "dosini", "properties", "conf")
    filenames = ("*.ini", "*.cfg", "*.conf", "*.properties", ".gitconfig", ".editorconfig")
    mimetypes = ("text/x-ini", "text/x-properties")

    rules = (
        # Comments
        Rule(re.compile(r"[;#].*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Section headers
        Rule(re.compile(r"^\s*\[[^\]]+\]", re.MULTILINE), TokenType.NAME_CLASS),
        # Keys (before = or :)
        Rule(re.compile(r"^[^=:\s][^=:]*(?=\s*[=:])", re.MULTILINE), TokenType.NAME_ATTRIBUTE),
        # Assignment operators
        Rule(re.compile(r"[=:]"), TokenType.OPERATOR),
        # Quoted values
        Rule(re.compile(r'"[^"]*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^']*'"), TokenType.STRING_SINGLE),
        # Boolean-like values
        Rule(
            re.compile(r"\b(?:true|false|yes|no|on|off)\b", re.IGNORECASE),
            TokenType.KEYWORD_CONSTANT,
        ),
        # Numbers
        Rule(re.compile(r"-?\d+\.\d*"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d+"), TokenType.NUMBER_INTEGER),
        # Variable interpolation
        Rule(re.compile(r"\$\{[^}]+\}"), TokenType.STRING_INTERPOL),
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.STRING_INTERPOL),
        Rule(re.compile(r"%[a-zA-Z_][a-zA-Z0-9_]*%"), TokenType.STRING_INTERPOL),
        # Values (everything else until end of line)
        Rule(re.compile(r"[^\s][^\n]*"), TokenType.STRING),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
