"""YAML lexer for Rosettes.

Thread-safe regex-based tokenizer for YAML documents.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["YamlLexer"]


def _classify_value(match: re.Match[str]) -> TokenType:
    """Classify a YAML value."""
    word = match.group(0).strip()
    lower = word.lower()
    if lower in ("true", "false", "yes", "no", "on", "off"):
        return TokenType.KEYWORD_CONSTANT
    if lower in ("null", "~"):
        return TokenType.KEYWORD_CONSTANT
    return TokenType.STRING


class YamlLexer(PatternLexer):
    """YAML lexer.

    Handles YAML 1.2 syntax including anchors, aliases, and multi-line strings.
    Thread-safe: all state is immutable.
    """

    name = "yaml"
    aliases = ("yml",)
    filenames = ("*.yaml", "*.yml")
    mimetypes = ("text/yaml", "application/x-yaml")

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Document markers
        Rule(re.compile(r"^---\s*$", re.MULTILINE), TokenType.PUNCTUATION_MARKER),
        Rule(re.compile(r"^\.\.\.\s*$", re.MULTILINE), TokenType.PUNCTUATION_MARKER),
        # Directives
        Rule(re.compile(r"^%[A-Z]+.*$", re.MULTILINE), TokenType.COMMENT_PREPROC),
        # Anchors and aliases
        Rule(re.compile(r"&[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_LABEL),
        Rule(re.compile(r"\*[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),
        # Tags
        Rule(re.compile(r"!![a-zA-Z]+"), TokenType.NAME_TAG),
        Rule(re.compile(r"![a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_TAG),
        # Keys (before colon)
        Rule(re.compile(r"[a-zA-Z_][a-zA-Z0-9_-]*(?=\s*:)"), TokenType.NAME_ATTRIBUTE),
        # Quoted strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        Rule(re.compile(r"'[^']*(?:''[^']*)*'"), TokenType.STRING),  # YAML single quotes
        # Block scalars
        Rule(re.compile(r"[|>][+-]?\d*\s*$", re.MULTILINE), TokenType.STRING_HEREDOC),
        # Numbers
        Rule(re.compile(r"-?\d+\.\d+(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d+[eE][+-]?\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"0x[0-9a-fA-F]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0o[0-7]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"-?\d+"), TokenType.NUMBER_INTEGER),
        # Boolean and null (as unquoted values)
        Rule(
            re.compile(r"\b(?:true|false|yes|no|on|off)\b", re.IGNORECASE),
            TokenType.KEYWORD_CONSTANT,
        ),
        Rule(re.compile(r"\b(?:null|~)\b"), TokenType.KEYWORD_CONSTANT),
        # Punctuation
        Rule(re.compile(r"[-:?>{}\[\],]"), TokenType.PUNCTUATION),
        # Unquoted strings (simplified - any word-like content)
        Rule(re.compile(r"[a-zA-Z_][a-zA-Z0-9_.-]*"), TokenType.STRING),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
