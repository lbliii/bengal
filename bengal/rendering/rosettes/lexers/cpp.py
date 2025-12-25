"""C++ lexer for Rosettes.

Thread-safe regex-based tokenizer for C++ source code.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["CppLexer"]

_KEYWORDS = (
    # C keywords
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
    "return",
    "sizeof",
    "static",
    "struct",
    "switch",
    "typedef",
    "union",
    "volatile",
    "while",
    # C++ keywords
    "alignas",
    "alignof",
    "and",
    "and_eq",
    "asm",
    "bitand",
    "bitor",
    "catch",
    "class",
    "compl",
    "concept",
    "const_cast",
    "consteval",
    "constexpr",
    "constinit",
    "co_await",
    "co_return",
    "co_yield",
    "decltype",
    "delete",
    "dynamic_cast",
    "explicit",
    "export",
    "final",
    "friend",
    "mutable",
    "namespace",
    "new",
    "noexcept",
    "not",
    "not_eq",
    "operator",
    "or",
    "or_eq",
    "override",
    "private",
    "protected",
    "public",
    "reinterpret_cast",
    "requires",
    "static_assert",
    "static_cast",
    "template",
    "this",
    "throw",
    "try",
    "typeid",
    "typename",
    "using",
    "virtual",
    "xor",
    "xor_eq",
)

_TYPES = (
    "bool",
    "char",
    "char8_t",
    "char16_t",
    "char32_t",
    "double",
    "float",
    "int",
    "long",
    "short",
    "signed",
    "unsigned",
    "void",
    "wchar_t",
    "size_t",
    "string",
    "vector",
    "map",
    "set",
    "list",
    "pair",
    "tuple",
    "unique_ptr",
    "shared_ptr",
    "weak_ptr",
    "optional",
    "variant",
    "any",
)

_CONSTANTS = ("true", "false", "nullptr", "NULL")


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in ("class", "struct", "enum", "union", "typedef", "namespace", "template"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("using", "namespace"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    return TokenType.NAME


class CppLexer(PatternLexer):
    """C++ lexer. Thread-safe."""

    name = "cpp"
    aliases = ("c++", "cxx", "hpp")
    filenames = ("*.cpp", "*.hpp", "*.cc", "*.hh", "*.cxx", "*.hxx")
    mimetypes = ("text/x-c++",)

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
        # Raw strings (C++11)
        Rule(re.compile(r'R"([^(]*)\([\s\S]*?\)\1"'), TokenType.STRING),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Characters
        Rule(re.compile(r"'[^'\\]'|'\\.'|'\\x[0-9a-fA-F]{1,2}'"), TokenType.STRING_CHAR),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F']+[uUlL]*"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[bB][01']+[uUlL]*"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"0[0-7']+[uUlL]*"), TokenType.NUMBER_OCT),
        Rule(
            re.compile(r"\d[\d']*\.\d[\d']*(?:[eE][+-]?\d[\d']*)?[fFlL]?"), TokenType.NUMBER_FLOAT
        ),
        Rule(re.compile(r"\.\d[\d']*(?:[eE][+-]?\d[\d']*)?[fFlL]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d']*[eE][+-]?\d[\d']*[fFlL]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d']*[uUlL]*"), TokenType.NUMBER_INTEGER),
        # Keywords/types/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"->|\.\.\.|::|\+\+|--"), TokenType.OPERATOR),
        Rule(re.compile(r"<=>|&&|\|\||==|!=|<=|>=|<<|>>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!~<>=?:]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
