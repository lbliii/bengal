"""Nim lexer for Rosettes.

Thread-safe regex-based tokenizer for Nim source code.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["NimLexer"]

_KEYWORDS = (
    "addr",
    "and",
    "as",
    "asm",
    "bind",
    "block",
    "break",
    "case",
    "cast",
    "concept",
    "const",
    "continue",
    "converter",
    "defer",
    "discard",
    "distinct",
    "div",
    "do",
    "elif",
    "else",
    "end",
    "enum",
    "except",
    "export",
    "finally",
    "for",
    "from",
    "func",
    "if",
    "import",
    "in",
    "include",
    "interface",
    "is",
    "isnot",
    "iterator",
    "let",
    "macro",
    "method",
    "mixin",
    "mod",
    "nil",
    "not",
    "notin",
    "object",
    "of",
    "or",
    "out",
    "proc",
    "ptr",
    "raise",
    "ref",
    "return",
    "shl",
    "shr",
    "static",
    "template",
    "try",
    "tuple",
    "type",
    "using",
    "var",
    "when",
    "while",
    "xor",
    "yield",
)

_TYPES = (
    "int",
    "int8",
    "int16",
    "int32",
    "int64",
    "uint",
    "uint8",
    "uint16",
    "uint32",
    "uint64",
    "float",
    "float32",
    "float64",
    "bool",
    "char",
    "string",
    "cstring",
    "pointer",
    "void",
    "auto",
    "any",
    "untyped",
    "typed",
    "seq",
    "array",
    "set",
    "tuple",
    "object",
    "ref",
    "ptr",
    "range",
    "openArray",
    "varargs",
    "sink",
    "lent",
)

_BUILTINS = (
    "abs",
    "add",
    "chr",
    "cmp",
    "contains",
    "copy",
    "dec",
    "del",
    "delete",
    "echo",
    "find",
    "high",
    "inc",
    "insert",
    "items",
    "len",
    "low",
    "max",
    "min",
    "newSeq",
    "newString",
    "ord",
    "pairs",
    "pop",
    "pred",
    "repr",
    "setLen",
    "sizeof",
    "succ",
    "swap",
    "typeof",
    "assert",
    "doAssert",
    "quit",
    "open",
    "close",
    "read",
    "readLine",
    "write",
    "writeLine",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("true", "false", "nil"):
        return TokenType.KEYWORD_CONSTANT
    if word in (
        "proc",
        "func",
        "method",
        "iterator",
        "converter",
        "macro",
        "template",
        "type",
        "const",
        "let",
        "var",
    ):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "export", "from", "include"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class NimLexer(PatternLexer):
    """Nim lexer. Thread-safe."""

    name = "nim"
    aliases = ("nimrod",)
    filenames = ("*.nim", "*.nims", "*.nimble")
    mimetypes = ("text/x-nim",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Documentation comments
        Rule(re.compile(r"##\[[\s\S]*?\]##"), TokenType.STRING_DOC),
        Rule(re.compile(r"##.*$", re.MULTILINE), TokenType.STRING_DOC),
        # Block comments
        Rule(re.compile(r"#\[[\s\S]*?\]#"), TokenType.COMMENT_MULTILINE),
        # Line comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Pragmas
        Rule(re.compile(r"\{\.[\s\S]*?\.\}"), TokenType.COMMENT_PREPROC),
        # Triple-quoted strings
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING_DOC),
        # Raw strings
        Rule(re.compile(r'r"[^"]*"'), TokenType.STRING),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Characters
        Rule(re.compile(r"'[^'\\]'|'\\.'|'\\x[0-9a-fA-F]{2}'"), TokenType.STRING_CHAR),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+(?:'[iuIU](?:8|16|32|64))?"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[oO][0-7_]+(?:'[iuIU](?:8|16|32|64))?"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"0[bB][01_]+(?:'[iuIU](?:8|16|32|64))?"), TokenType.NUMBER_BIN),
        Rule(
            re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?(?:'[fFdD](?:32|64|128)?)?"),
            TokenType.NUMBER_FLOAT,
        ),
        Rule(
            re.compile(r"\d[\d_]*[eE][+-]?\d[\d_]*(?:'[fFdD](?:32|64|128)?)?"),
            TokenType.NUMBER_FLOAT,
        ),
        Rule(re.compile(r"\d[\d_]*(?:'[iuIUfFdD](?:8|16|32|64|128)?)?"), TokenType.NUMBER_INTEGER),
        # Generics/templates
        Rule(re.compile(r"`[^`]+`"), TokenType.NAME),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"->|=>|<-|\.\.|\.\.<?"), TokenType.OPERATOR),
        Rule(re.compile(r"==|!=|<=|>=|<<|>>|and|or|not|xor|shl|shr|div|mod"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|&=|\|=|\^="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/@$%&|^!~<>=?:]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
