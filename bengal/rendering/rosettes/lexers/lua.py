"""Lua lexer for Rosettes.

Thread-safe regex-based tokenizer for Lua source code.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["LuaLexer"]

_KEYWORDS = (
    "and",
    "break",
    "do",
    "else",
    "elseif",
    "end",
    "for",
    "function",
    "goto",
    "if",
    "in",
    "local",
    "not",
    "or",
    "repeat",
    "return",
    "then",
    "until",
    "while",
)

_BUILTINS = (
    "assert",
    "collectgarbage",
    "dofile",
    "error",
    "getmetatable",
    "ipairs",
    "load",
    "loadfile",
    "next",
    "pairs",
    "pcall",
    "print",
    "rawequal",
    "rawget",
    "rawlen",
    "rawset",
    "require",
    "select",
    "setmetatable",
    "tonumber",
    "tostring",
    "type",
    "xpcall",
    "_G",
    "_VERSION",
)

_CONSTANTS = ("true", "false", "nil")


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in ("function", "local"):
        return TokenType.KEYWORD_DECLARATION
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class LuaLexer(PatternLexer):
    """Lua lexer. Thread-safe."""

    name = "lua"
    aliases = ()
    filenames = ("*.lua", "*.wlua")
    mimetypes = ("text/x-lua", "application/x-lua")

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"--\[\[[\s\S]*?\]\]"), TokenType.COMMENT_MULTILINE),
        Rule(re.compile(r"--\[=+\[[\s\S]*?\]=+\]"), TokenType.COMMENT_MULTILINE),
        Rule(re.compile(r"--.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Long strings
        Rule(re.compile(r"\[\[[\s\S]*?\]\]"), TokenType.STRING),
        Rule(re.compile(r"\[=+\[[\s\S]*?\]=+\]"), TokenType.STRING),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Labels (goto targets)
        Rule(re.compile(r"::[a-zA-Z_][a-zA-Z0-9_]*::"), TokenType.NAME_LABEL),
        # Numbers
        Rule(
            re.compile(r"0[xX][0-9a-fA-F]+(?:\.[0-9a-fA-F]*)?(?:[pP][+-]?\d+)?"),
            TokenType.NUMBER_HEX,
        ),
        Rule(re.compile(r"\d+\.\d*(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\.\d+(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[eE][+-]?\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"\.\.\.?|~=|==|<=|>=|<<|>>|//"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%^#<>=&|~]"), TokenType.OPERATOR),
        # Method call
        Rule(re.compile(r":"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}.,;]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
