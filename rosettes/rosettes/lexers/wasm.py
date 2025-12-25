"""WebAssembly Text Format (WAT) lexer for Rosettes.

Thread-safe regex-based tokenizer for WebAssembly text format.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["WasmLexer"]

# WAT keywords
_KEYWORDS = frozenset(
    (
        "module",
        "type",
        "func",
        "param",
        "result",
        "local",
        "global",
        "table",
        "memory",
        "elem",
        "data",
        "start",
        "import",
        "export",
        "mut",
        "offset",
        "block",
        "loop",
        "if",
        "then",
        "else",
        "end",
        "br",
        "br_if",
        "br_table",
        "return",
        "call",
        "call_indirect",
        "drop",
        "select",
        "unreachable",
        "nop",
    )
)

# WAT types
_TYPES = frozenset(
    (
        "i32",
        "i64",
        "f32",
        "f64",
        "v128",
        "funcref",
        "externref",
        "anyfunc",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify WAT identifiers."""
    word = match.group(0)
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    # Instructions (most start with type prefix)
    if word.startswith(("i32.", "i64.", "f32.", "f64.", "v128.", "memory.", "table.")):
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class WasmLexer(PatternLexer):
    """WebAssembly Text Format (WAT) lexer. Thread-safe."""

    name = "wasm"
    aliases = ("wat", "wast", "webassembly")
    filenames = ("*.wat", "*.wast")
    mimetypes = ("text/x-wat",)

    rules = (
        # Comments
        Rule(re.compile(r";;.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"\(;.*?;\)", re.DOTALL), TokenType.COMMENT_MULTILINE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        # Identifiers: $name
        Rule(re.compile(r"\$[a-zA-Z0-9_!#$%&'*+\-./:<=>?@\\^`|~]+"), TokenType.NAME_VARIABLE),
        # Hex numbers
        Rule(re.compile(r"-?0x[0-9a-fA-F][0-9a-fA-F_]*"), TokenType.NUMBER_HEX),
        # Float numbers
        Rule(re.compile(r"-?\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?inf|nan(?::0x[0-9a-fA-F]+)?"), TokenType.NUMBER_FLOAT),
        # Integer numbers
        Rule(re.compile(r"-?\d[\d_]*"), TokenType.NUMBER_INTEGER),
        # Instructions and keywords
        Rule(re.compile(r"[a-z][a-z0-9_.]*"), _classify_word),
        # Parentheses (S-expressions)
        Rule(re.compile(r"[()]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
