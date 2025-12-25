"""Elixir lexer for Rosettes.

Thread-safe regex-based tokenizer for Elixir source code.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["ElixirLexer"]

_KEYWORDS = (
    "after",
    "and",
    "case",
    "catch",
    "cond",
    "do",
    "else",
    "end",
    "fn",
    "for",
    "if",
    "in",
    "not",
    "or",
    "quote",
    "raise",
    "receive",
    "rescue",
    "try",
    "unless",
    "unquote",
    "unquote_splicing",
    "when",
    "with",
)

_DECLARATIONS = (
    "def",
    "defp",
    "defmacro",
    "defmacrop",
    "defmodule",
    "defprotocol",
    "defimpl",
    "defstruct",
    "defdelegate",
    "defexception",
    "defguard",
    "defguardp",
    "defcallback",
    "defoverridable",
)

_BUILTINS = (
    "alias",
    "case",
    "cond",
    "for",
    "if",
    "import",
    "quote",
    "raise",
    "receive",
    "require",
    "reraise",
    "super",
    "throw",
    "try",
    "unless",
    "unquote",
    "unquote_splicing",
    "use",
    "with",
)

_PSEUDO = ("__MODULE__", "__DIR__", "__ENV__", "__CALLER__", "__STACKTRACE__")


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("true", "false", "nil"):
        return TokenType.KEYWORD_CONSTANT
    if word in _PSEUDO:
        return TokenType.NAME_BUILTIN_PSEUDO
    if word in _DECLARATIONS:
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "require", "use", "alias"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class ElixirLexer(PatternLexer):
    """Elixir lexer. Thread-safe."""

    name = "elixir"
    aliases = ("ex", "exs")
    filenames = ("*.ex", "*.exs")
    mimetypes = ("text/x-elixir",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*[?!]?\b"

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Module attributes
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_DECORATOR),
        # Sigils with heredoc delimiters
        Rule(re.compile(r'~[a-zA-Z]"""[\s\S]*?"""[a-zA-Z]*'), TokenType.STRING),
        Rule(re.compile(r"~[a-zA-Z]'''[\s\S]*?'''[a-zA-Z]*"), TokenType.STRING),
        # Sigils
        Rule(re.compile(r"~[rRsSwWcCdDnNtT]/[^/]*/[a-zA-Z]*"), TokenType.STRING_REGEX),
        Rule(re.compile(r"~[rRsSwWcCdDnNtT]\{[^}]*\}[a-zA-Z]*"), TokenType.STRING),
        Rule(re.compile(r"~[rRsSwWcCdDnNtT]\[[^\]]*\][a-zA-Z]*"), TokenType.STRING),
        Rule(re.compile(r"~[rRsSwWcCdDnNtT]\([^)]*\)[a-zA-Z]*"), TokenType.STRING),
        Rule(re.compile(r'~[rRsSwWcCdDnNtT]"[^"]*"[a-zA-Z]*'), TokenType.STRING),
        Rule(re.compile(r"~[rRsSwWcCdDnNtT]'[^']*'[a-zA-Z]*"), TokenType.STRING),
        # Heredoc strings
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING_DOC),
        Rule(re.compile(r"'''[\s\S]*?'''"), TokenType.STRING_DOC),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_CHAR),
        # Atoms
        Rule(re.compile(r":[a-zA-Z_][a-zA-Z0-9_]*[?!]?"), TokenType.STRING_SYMBOL),
        Rule(re.compile(r':"[^"]*"'), TokenType.STRING_SYMBOL),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[oO][0-7_]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"0[bB][01_]+"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?\d[\d_]*"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*"), TokenType.NUMBER_INTEGER),
        # Special atoms
        Rule(re.compile(r"\b(?:true|false|nil)\b"), TokenType.KEYWORD_CONSTANT),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"<>|<-|->|\|>|~>>|<<~|~>|<~>|<~|::"), TokenType.OPERATOR),
        Rule(re.compile(r"\+\+|--|<>|\\\\"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|=~|===|!==|<=|>=|<|>"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%^&|!=<>]"), TokenType.OPERATOR),
        # Capture operator
        Rule(re.compile(r"&\d+"), TokenType.NAME_VARIABLE),
        Rule(re.compile(r"&"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}.,;]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
