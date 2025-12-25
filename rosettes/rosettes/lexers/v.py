"""V lexer for Rosettes.

Thread-safe regex-based tokenizer for V programming language.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["VLexer"]

_KEYWORDS = (
    "as",
    "asm",
    "assert",
    "atomic",
    "break",
    "const",
    "continue",
    "defer",
    "else",
    "enum",
    "false",
    "fn",
    "for",
    "go",
    "goto",
    "if",
    "import",
    "in",
    "interface",
    "is",
    "isreftype",
    "lock",
    "match",
    "module",
    "mut",
    "none",
    "or",
    "pub",
    "return",
    "rlock",
    "select",
    "shared",
    "sizeof",
    "spawn",
    "static",
    "struct",
    "true",
    "type",
    "typeof",
    "union",
    "unsafe",
    "volatile",
    "__offsetof",
)

_TYPES = (
    "bool",
    "string",
    "i8",
    "i16",
    "i32",
    "i64",
    "i128",
    "int",
    "u8",
    "u16",
    "u32",
    "u64",
    "u128",
    "byte",
    "rune",
    "f32",
    "f64",
    "voidptr",
    "charptr",
    "byteptr",
    "any",
    "none",
)

_BUILTINS = (
    "eprint",
    "eprintln",
    "print",
    "println",
    "dump",
    "panic",
    "exit",
    "error",
    "typeof",
    "sizeof",
    "isnil",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("true", "false", "none"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("fn", "struct", "enum", "interface", "union", "type", "const", "mut"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "module", "pub"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class VLexer(PatternLexer):
    """V lexer. Thread-safe."""

    name = "v"
    aliases = ("vlang",)
    filenames = ("*.v", "*.vv")
    mimetypes = ("text/x-v",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Attributes
        Rule(
            re.compile(r"\[[\w;:,\s]+\](?=\s*(?:fn|struct|enum|interface|pub|mut|const))"),
            TokenType.NAME_DECORATOR,
        ),
        # Raw strings
        Rule(re.compile(r"r'[^']*'"), TokenType.STRING),
        Rule(re.compile(r'r"[^"]*"'), TokenType.STRING),
        # Strings
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        # Characters
        Rule(re.compile(r"`[^`\\]`|`\\.`"), TokenType.STRING_CHAR),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[oO][0-7_]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"0[bB][01_]+"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?\d[\d_]*"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*"), TokenType.NUMBER_INTEGER),
        # Optional marker
        Rule(re.compile(r"\?"), TokenType.OPERATOR),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"<-|->|\.\.\.?|\$"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<<|>>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!~<>=]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
