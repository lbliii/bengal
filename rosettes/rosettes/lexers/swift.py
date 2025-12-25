"""Swift lexer for Rosettes.

Thread-safe regex-based tokenizer for Swift source code.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["SwiftLexer"]

_KEYWORDS = (
    "actor",
    "any",
    "as",
    "associatedtype",
    "async",
    "await",
    "break",
    "case",
    "catch",
    "class",
    "continue",
    "default",
    "defer",
    "deinit",
    "do",
    "else",
    "enum",
    "extension",
    "fallthrough",
    "fileprivate",
    "for",
    "func",
    "guard",
    "if",
    "import",
    "in",
    "init",
    "inout",
    "internal",
    "is",
    "let",
    "macro",
    "nonisolated",
    "open",
    "operator",
    "precedencegroup",
    "private",
    "protocol",
    "public",
    "repeat",
    "rethrows",
    "return",
    "self",
    "Self",
    "some",
    "static",
    "struct",
    "subscript",
    "super",
    "switch",
    "throw",
    "throws",
    "try",
    "typealias",
    "var",
    "where",
    "while",
)

_TYPES = (
    "Any",
    "AnyObject",
    "Array",
    "Bool",
    "Character",
    "Dictionary",
    "Double",
    "Float",
    "Int",
    "Int8",
    "Int16",
    "Int32",
    "Int64",
    "Never",
    "Optional",
    "Result",
    "Set",
    "String",
    "UInt",
    "UInt8",
    "UInt16",
    "UInt32",
    "UInt64",
    "Void",
)

_CONSTANTS = ("true", "false", "nil")


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in (
        "class",
        "struct",
        "enum",
        "protocol",
        "extension",
        "func",
        "var",
        "let",
        "typealias",
        "actor",
    ):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import",):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class SwiftLexer(PatternLexer):
    """Swift lexer. Thread-safe."""

    name = "swift"
    aliases = ()
    filenames = ("*.swift",)
    mimetypes = ("text/x-swift",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*\*[\s\S]*?\*/"), TokenType.STRING_DOC),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Attributes
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_DECORATOR),
        # Preprocessor
        Rule(
            re.compile(
                r"#(?:if|elseif|else|endif|available|sourceLocation|warning|error).*$", re.MULTILINE
            ),
            TokenType.COMMENT_PREPROC,
        ),
        # Multi-line strings
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING_DOC),
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
        Rule(re.compile(r"->|\.\.\.|\.\.<|\.\."), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|===|!==|<=|>=|<<|>>"), TokenType.OPERATOR),
        Rule(re.compile(r"\?\?|\?\.|\?|!"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^~<>=]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
