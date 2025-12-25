"""Protocol Buffers lexer for Rosettes.

Thread-safe regex-based tokenizer for Protocol Buffer definitions.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["ProtobufLexer"]

_KEYWORDS = (
    "default",
    "enum",
    "extend",
    "extensions",
    "group",
    "import",
    "map",
    "max",
    "message",
    "oneof",
    "option",
    "optional",
    "package",
    "public",
    "repeated",
    "required",
    "reserved",
    "returns",
    "rpc",
    "service",
    "stream",
    "syntax",
    "to",
    "weak",
)

_TYPES = (
    "bool",
    "bytes",
    "double",
    "fixed32",
    "fixed64",
    "float",
    "int32",
    "int64",
    "sfixed32",
    "sfixed64",
    "sint32",
    "sint64",
    "string",
    "uint32",
    "uint64",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("true", "false"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("message", "enum", "service", "rpc", "oneof"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "package", "syntax"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class ProtobufLexer(PatternLexer):
    """Protocol Buffers lexer. Thread-safe."""

    name = "protobuf"
    aliases = ("proto", "proto3")
    filenames = ("*.proto",)
    mimetypes = ("text/x-protobuf",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"\d+\.\d*(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+"), TokenType.NUMBER_INTEGER),
        # Field numbers (after = sign)
        Rule(re.compile(r"=\s*\d+"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"[=]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.<>]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
