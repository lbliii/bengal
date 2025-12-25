"""CUE lexer for Rosettes.

Thread-safe regex-based tokenizer for CUE configuration language.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["CueLexer"]

_KEYWORDS = (
    "package",
    "import",
    "let",
    "if",
    "for",
    "in",
)

_TYPES = (
    "bool",
    "string",
    "bytes",
    "number",
    "int",
    "float",
    "null",
    "uint",
    "int8",
    "int16",
    "int32",
    "int64",
    "int128",
    "uint8",
    "uint16",
    "uint32",
    "uint64",
    "uint128",
    "float32",
    "float64",
    "rune",
)

_BUILTINS = (
    "len",
    "close",
    "and",
    "or",
    "div",
    "mod",
    "quo",
    "rem",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("true", "false", "null"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("let",):
        return TokenType.KEYWORD_DECLARATION
    if word in ("package", "import"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    if word[0] == "_":
        return TokenType.NAME_VARIABLE  # Hidden fields
    if word[0] == "#":
        return TokenType.NAME_CLASS  # Definitions
    return TokenType.NAME


class CueLexer(PatternLexer):
    """CUE lexer. Thread-safe."""

    name = "cue"
    aliases = ()
    filenames = ("*.cue",)
    mimetypes = ("text/x-cue",)

    _WORD_PATTERN = r"\b[_#]?[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Multi-line strings
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING),
        Rule(re.compile(r"'''[\s\S]*?'''"), TokenType.STRING),
        Rule(re.compile(r"#\"\"\"[\s\S]*?\"\"\"#"), TokenType.STRING),
        Rule(re.compile(r"#'''[\s\S]*?'''#"), TokenType.STRING),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING),
        Rule(re.compile(r"#\"[^\"]*\"#"), TokenType.STRING),
        Rule(re.compile(r"#'[^']*'#"), TokenType.STRING),
        # Bytes
        Rule(re.compile(r"'[^']*'"), TokenType.STRING),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[oO][0-7_]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"0[bB][01_]+"), TokenType.NUMBER_BIN),
        Rule(
            re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?[KMGTPkmgtp]?i?"),
            TokenType.NUMBER_FLOAT,
        ),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?\d[\d_]*"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[KMGTPkmgtp]?i?"), TokenType.NUMBER_INTEGER),
        # Definition markers
        Rule(re.compile(r"#[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_CLASS),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"[=!<>]=?|&&|\|\||[&|]"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*]"), TokenType.OPERATOR),
        Rule(re.compile(r"\.\.\."), TokenType.OPERATOR),
        # Constraints
        Rule(re.compile(r"[<>=!]=?"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
