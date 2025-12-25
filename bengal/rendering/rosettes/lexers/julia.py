"""Julia lexer for Rosettes.

Thread-safe regex-based tokenizer for Julia source code.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["JuliaLexer"]

_KEYWORDS = (
    "baremodule",
    "begin",
    "break",
    "catch",
    "const",
    "continue",
    "do",
    "else",
    "elseif",
    "end",
    "export",
    "finally",
    "for",
    "function",
    "global",
    "if",
    "import",
    "let",
    "local",
    "macro",
    "module",
    "mutable",
    "outer",
    "quote",
    "return",
    "struct",
    "try",
    "using",
    "where",
    "while",
)

_TYPES = (
    "AbstractArray",
    "AbstractDict",
    "AbstractFloat",
    "AbstractMatrix",
    "AbstractSet",
    "AbstractString",
    "AbstractVector",
    "Any",
    "Array",
    "Bool",
    "Char",
    "Complex",
    "Dict",
    "Float16",
    "Float32",
    "Float64",
    "Function",
    "Int",
    "Int8",
    "Int16",
    "Int32",
    "Int64",
    "Int128",
    "Integer",
    "IO",
    "Matrix",
    "Nothing",
    "Number",
    "Pair",
    "Rational",
    "Real",
    "Set",
    "Signed",
    "String",
    "Symbol",
    "Tuple",
    "Type",
    "UInt",
    "UInt8",
    "UInt16",
    "UInt32",
    "UInt64",
    "UInt128",
    "Union",
    "Unsigned",
    "Vector",
)

_BUILTINS = (
    "abs",
    "all",
    "any",
    "append!",
    "broadcast",
    "cat",
    "collect",
    "copy",
    "delete!",
    "display",
    "div",
    "dump",
    "eachindex",
    "eltype",
    "enumerate",
    "error",
    "exp",
    "fill",
    "filter",
    "findfirst",
    "findlast",
    "first",
    "floor",
    "foreach",
    "get",
    "getfield",
    "getindex",
    "haskey",
    "hcat",
    "identity",
    "in",
    "insert!",
    "isa",
    "isempty",
    "isnothing",
    "iterate",
    "join",
    "keys",
    "last",
    "length",
    "log",
    "map",
    "mapreduce",
    "max",
    "maximum",
    "merge",
    "min",
    "minimum",
    "mod",
    "ndims",
    "nothing",
    "ones",
    "pairs",
    "parse",
    "pop!",
    "popfirst!",
    "print",
    "println",
    "prod",
    "push!",
    "pushfirst!",
    "rand",
    "range",
    "read",
    "readline",
    "reduce",
    "rem",
    "repeat",
    "repr",
    "reshape",
    "reverse",
    "round",
    "setfield!",
    "setindex!",
    "show",
    "similar",
    "size",
    "sizeof",
    "skipmissing",
    "sleep",
    "sort",
    "sort!",
    "sortperm",
    "split",
    "sprint",
    "sqrt",
    "string",
    "strip",
    "sum",
    "take!",
    "throw",
    "tuple",
    "typeof",
    "unique",
    "values",
    "vcat",
    "write",
    "zero",
    "zeros",
    "zip",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("true", "false", "nothing", "missing", "Inf", "NaN"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("function", "macro", "struct", "mutable", "const", "module", "baremodule"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "using", "export", "module"):
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


class JuliaLexer(PatternLexer):
    """Julia lexer. Thread-safe."""

    name = "julia"
    aliases = ("jl",)
    filenames = ("*.jl",)
    mimetypes = ("text/x-julia",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_!]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"#=[\s\S]*?=#"), TokenType.COMMENT_MULTILINE),
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Triple-quoted strings
        Rule(re.compile(r'"""[\s\S]*?"""'), TokenType.STRING_DOC),
        # Command literals
        Rule(re.compile(r"`[^`]*`"), TokenType.STRING_BACKTICK),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Characters
        Rule(re.compile(r"'[^'\\]'|'\\.'|'\\u[0-9a-fA-F]{1,6}'"), TokenType.STRING_CHAR),
        # Symbols
        Rule(re.compile(r":[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.STRING_SYMBOL),
        # Macros
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_!]*"), TokenType.NAME_DECORATOR),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[oO][0-7_]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"0[bB][01_]+"), TokenType.NUMBER_BIN),
        Rule(
            re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eEfF][+-]?\d[\d_]*)?(?:im)?"), TokenType.NUMBER_FLOAT
        ),
        Rule(re.compile(r"\d[\d_]*[eEfF][+-]?\d[\d_]*(?:im)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*(?:im)?"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"\.\.\.?|->|<:|>:|::"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||===|!==|==|!=|<=|>=|<<|>>>|>>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|÷=|%=|^=|&=|\|=|⊻=|<<=|>>=|>>>="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/÷%^&|⊻!~<>=\\']"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
