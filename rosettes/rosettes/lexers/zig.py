"""Zig lexer for Rosettes.

Thread-safe regex-based tokenizer for Zig source code.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["ZigLexer"]

_KEYWORDS = (
    "addrspace",
    "align",
    "allowzero",
    "and",
    "anyframe",
    "anytype",
    "asm",
    "async",
    "await",
    "break",
    "callconv",
    "catch",
    "comptime",
    "const",
    "continue",
    "defer",
    "else",
    "enum",
    "errdefer",
    "error",
    "export",
    "extern",
    "fn",
    "for",
    "if",
    "inline",
    "linksection",
    "noalias",
    "noinline",
    "nosuspend",
    "opaque",
    "or",
    "orelse",
    "packed",
    "pub",
    "resume",
    "return",
    "struct",
    "suspend",
    "switch",
    "test",
    "threadlocal",
    "try",
    "union",
    "unreachable",
    "usingnamespace",
    "var",
    "volatile",
    "while",
)

_TYPES = (
    "i8",
    "i16",
    "i32",
    "i64",
    "i128",
    "isize",
    "u8",
    "u16",
    "u32",
    "u64",
    "u128",
    "usize",
    "f16",
    "f32",
    "f64",
    "f80",
    "f128",
    "bool",
    "void",
    "noreturn",
    "type",
    "anyerror",
    "comptime_int",
    "comptime_float",
    "c_short",
    "c_ushort",
    "c_int",
    "c_uint",
    "c_long",
    "c_ulong",
    "c_longlong",
    "c_ulonglong",
    "c_longdouble",
    "c_void",
)

_BUILTINS = (
    "@addWithOverflow",
    "@alignCast",
    "@alignOf",
    "@as",
    "@atomicLoad",
    "@atomicRmw",
    "@atomicStore",
    "@bitCast",
    "@bitOffsetOf",
    "@boolToInt",
    "@breakpoint",
    "@byteSwap",
    "@call",
    "@cDefine",
    "@ceil",
    "@cImport",
    "@cInclude",
    "@clz",
    "@cmpxchgStrong",
    "@cmpxchgWeak",
    "@compileError",
    "@compileLog",
    "@ctz",
    "@cUndef",
    "@divExact",
    "@divFloor",
    "@divTrunc",
    "@embedFile",
    "@enumToInt",
    "@errSetCast",
    "@errorName",
    "@errorReturnTrace",
    "@exp",
    "@exp2",
    "@export",
    "@extern",
    "@fabs",
    "@fence",
    "@field",
    "@fieldParentPtr",
    "@floatCast",
    "@floatToInt",
    "@floor",
    "@frame",
    "@Frame",
    "@frameAddress",
    "@frameSize",
    "@hasDecl",
    "@hasField",
    "@import",
    "@intCast",
    "@intToEnum",
    "@intToFloat",
    "@intToPtr",
    "@log",
    "@log10",
    "@log2",
    "@max",
    "@memcpy",
    "@memset",
    "@min",
    "@mod",
    "@mulWithOverflow",
    "@panic",
    "@popCount",
    "@prefetch",
    "@ptrCast",
    "@ptrToInt",
    "@reduce",
    "@rem",
    "@returnAddress",
    "@round",
    "@select",
    "@setAlignStack",
    "@setCold",
    "@setEvalBranchQuota",
    "@setFloatMode",
    "@setRuntimeSafety",
    "@shlExact",
    "@shlWithOverflow",
    "@shrExact",
    "@shuffle",
    "@sin",
    "@sizeOf",
    "@splat",
    "@sqrt",
    "@src",
    "@subWithOverflow",
    "@tagName",
    "@This",
    "@trap",
    "@truncate",
    "@trunc",
    "@Type",
    "@typeInfo",
    "@typeName",
    "@TypeOf",
    "@unionInit",
    "@Vector",
    "@wasmMemoryGrow",
    "@wasmMemorySize",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("true", "false", "null", "undefined"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("fn", "struct", "enum", "union", "const", "var", "test"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("usingnamespace",):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    return TokenType.NAME


class ZigLexer(PatternLexer):
    """Zig lexer. Thread-safe."""

    name = "zig"
    aliases = ()
    filenames = ("*.zig",)
    mimetypes = ("text/x-zig",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"///.*$", re.MULTILINE), TokenType.STRING_DOC),
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Builtin functions
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_BUILTIN),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Multi-line strings
        Rule(re.compile(r"\\\\[^\n]*"), TokenType.STRING),
        # Characters
        Rule(
            re.compile(r"'[^'\\]'|'\\.'|'\\x[0-9a-fA-F]{2}'|'\\u\{[0-9a-fA-F]+\}'"),
            TokenType.STRING_CHAR,
        ),
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
        Rule(re.compile(r"=>|->|\.\.\.|\.\.|\.\*|\+\+|--"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<<|>>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+%|-%|\*%|<<%"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!~<>=?]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
