"""C lexer for Rosettes.

Thread-safe regex-based tokenizer for C source code.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["CLexer"]

_KEYWORDS = (
    "auto",
    "break",
    "case",
    "const",
    "continue",
    "default",
    "do",
    "else",
    "enum",
    "extern",
    "for",
    "goto",
    "if",
    "inline",
    "register",
    "restrict",
    "return",
    "sizeof",
    "static",
    "struct",
    "switch",
    "typedef",
    "union",
    "volatile",
    "while",
    "_Alignas",
    "_Alignof",
    "_Atomic",
    "_Bool",
    "_Complex",
    "_Generic",
    "_Imaginary",
    "_Noreturn",
    "_Static_assert",
    "_Thread_local",
)

_TYPES = (
    "char",
    "double",
    "float",
    "int",
    "long",
    "short",
    "signed",
    "unsigned",
    "void",
    "size_t",
    "ssize_t",
    "ptrdiff_t",
    "int8_t",
    "int16_t",
    "int32_t",
    "int64_t",
    "uint8_t",
    "uint16_t",
    "uint32_t",
    "uint64_t",
    "bool",
    "FILE",
    "NULL",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("NULL",):
        return TokenType.KEYWORD_CONSTANT
    if word in ("struct", "enum", "union", "typedef"):
        return TokenType.KEYWORD_DECLARATION
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    return TokenType.NAME


class CLexer(PatternLexer):
    """C lexer. Thread-safe."""

    name = "c"
    aliases = ("h",)
    filenames = ("*.c", "*.h")
    mimetypes = ("text/x-c",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Preprocessor
        Rule(
            re.compile(
                r"#\s*(?:include|define|undef|ifdef|ifndef|if|elif|else|endif|pragma|error|warning).*$",
                re.MULTILINE,
            ),
            TokenType.COMMENT_PREPROC,
        ),
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Characters
        Rule(
            re.compile(r"'[^'\\]'|'\\.'|'\\x[0-9a-fA-F]{1,2}'|'\\[0-7]{1,3}'"),
            TokenType.STRING_CHAR,
        ),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F]+[uUlL]*"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[0-7]+[uUlL]*"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"\d+\.\d*(?:[eE][+-]?\d+)?[fFlL]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\.\d+(?:[eE][+-]?\d+)?[fFlL]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[eE][+-]?\d+[fFlL]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[uUlL]*"), TokenType.NUMBER_INTEGER),
        # Keywords/types/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"->|\.\.\.|\+\+|--"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<<|>>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!~<>=?:]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
