"""Rust lexer for Rosettes.

Thread-safe regex-based tokenizer for Rust source code.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["RustLexer"]

_KEYWORDS = (
    "as",
    "async",
    "await",
    "break",
    "const",
    "continue",
    "crate",
    "dyn",
    "else",
    "enum",
    "extern",
    "false",
    "fn",
    "for",
    "if",
    "impl",
    "in",
    "let",
    "loop",
    "match",
    "mod",
    "move",
    "mut",
    "pub",
    "ref",
    "return",
    "self",
    "Self",
    "static",
    "struct",
    "super",
    "trait",
    "true",
    "type",
    "unsafe",
    "use",
    "where",
    "while",
)

_TYPES = (
    "bool",
    "char",
    "f32",
    "f64",
    "i8",
    "i16",
    "i32",
    "i64",
    "i128",
    "isize",
    "str",
    "u8",
    "u16",
    "u32",
    "u64",
    "u128",
    "usize",
    "Option",
    "Result",
    "String",
    "Vec",
    "Box",
    "Rc",
    "Arc",
    "Cell",
    "RefCell",
)


def _classify_keyword(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("true", "false"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("fn", "struct", "enum", "trait", "type", "impl", "mod", "const", "static", "let"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("use", "crate", "mod", "super", "self", "Self"):
        return TokenType.KEYWORD_NAMESPACE
    return TokenType.KEYWORD


def _classify_name(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _TYPES:
        return TokenType.NAME_BUILTIN
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class RustLexer(PatternLexer):
    """Rust lexer. Thread-safe."""

    name = "rust"
    aliases = ("rs",)
    filenames = ("*.rs",)
    mimetypes = ("text/rust", "text/x-rust")

    _KEYWORD_PATTERN = r"\b(?:" + "|".join(_KEYWORDS) + r")\b"
    _NAME_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Attributes
        Rule(re.compile(r"#!?\[[^\]]*\]"), TokenType.NAME_DECORATOR),
        # Lifetimes
        Rule(re.compile(r"'[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_LABEL),
        # Raw strings
        Rule(re.compile(r'r#*"[^"]*"#*'), TokenType.STRING),
        # Byte strings
        Rule(re.compile(r'b"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        Rule(re.compile(r"b'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_CHAR),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Characters
        Rule(re.compile(r"'[^'\\]'|'\\.'"), TokenType.STRING_CHAR),
        # Numbers
        Rule(
            re.compile(r"0x[0-9a-fA-F_]+(?:i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize)?"),
            TokenType.NUMBER_HEX,
        ),
        Rule(
            re.compile(r"0o[0-7_]+(?:i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize)?"),
            TokenType.NUMBER_OCT,
        ),
        Rule(
            re.compile(r"0b[01_]+(?:i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize)?"),
            TokenType.NUMBER_BIN,
        ),
        Rule(
            re.compile(r"\d[\d_]*\.[\d_]*(?:[eE][+-]?[\d_]+)?(?:f32|f64)?"), TokenType.NUMBER_FLOAT
        ),
        Rule(
            re.compile(r"\d[\d_]*(?:i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize)?"),
            TokenType.NUMBER_INTEGER,
        ),
        # Keywords
        Rule(re.compile(_KEYWORD_PATTERN), _classify_keyword),
        # Macros
        Rule(re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*!"), TokenType.NAME_FUNCTION_MAGIC),
        # Names
        Rule(re.compile(_NAME_PATTERN), _classify_name),
        # Operators
        Rule(re.compile(r"=>|->|::|\.\.|\.\.="), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<<|>>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!<>=?]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
