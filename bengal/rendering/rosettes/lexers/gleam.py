"""Gleam lexer for Rosettes.

Thread-safe regex-based tokenizer for Gleam source code.
Gleam is a type-safe functional language for the Erlang VM.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["GleamLexer"]

_KEYWORDS = (
    "as",
    "assert",
    "auto",
    "case",
    "const",
    "delegate",
    "derive",
    "echo",
    "else",
    "fn",
    "if",
    "implement",
    "import",
    "let",
    "macro",
    "opaque",
    "panic",
    "pub",
    "test",
    "todo",
    "type",
    "use",
)

_TYPES = (
    "Int",
    "Float",
    "String",
    "Bool",
    "List",
    "Result",
    "Option",
    "Nil",
    "BitArray",
    "Dict",
    "Set",
    "Iterator",
    "Queue",
    "Uri",
    "Dynamic",
)

_BUILTINS = (
    "Ok",
    "Error",
    "Some",
    "None",
    "True",
    "False",
    "Nil",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("True", "False", "Nil"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("fn", "type", "const", "let", "pub"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "use"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES or word in _BUILTINS:
        return TokenType.KEYWORD_TYPE
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class GleamLexer(PatternLexer):
    """Gleam lexer. Thread-safe."""

    name = "gleam"
    aliases = ()
    filenames = ("*.gleam",)
    mimetypes = ("text/x-gleam",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"////.*$", re.MULTILINE), TokenType.STRING_DOC),
        Rule(re.compile(r"///.*$", re.MULTILINE), TokenType.STRING_DOC),
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Attributes
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_DECORATOR),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[oO][0-7_]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"0[bB][01_]+"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?\d[\d_]*"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"->|<-|\|>|\.\."), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<\.|>\.|<|>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+\.|-\.|\*\.|/\."), TokenType.OPERATOR),  # Float operators
        Rule(re.compile(r"[+\-*/%&|^!<>=]"), TokenType.OPERATOR),
        # Pipe
        Rule(re.compile(r"\|"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,#]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
