"""Hand-written Zig lexer using state machine approach.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._config import LexerConfig
from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    BINARY_DIGITS,
    DIGITS,
    HEX_DIGITS,
    OCTAL_DIGITS,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["ZigStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
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
    }
)

_TYPES: frozenset[str] = frozenset(
    {
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
        "c_int",
        "c_long",
        "c_longlong",
        "c_ushort",
        "c_uint",
        "c_ulong",
        "c_ulonglong",
        "c_char",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "null", "undefined"})

_BUILTINS: frozenset[str] = frozenset(
    {
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
        "@clz",
        "@cmpxchgStrong",
        "@cmpxchgWeak",
        "@compileError",
        "@compileLog",
        "@ctz",
        "@divExact",
        "@divFloor",
        "@divTrunc",
        "@embedFile",
        "@enumToInt",
        "@errSetCast",
        "@errorName",
        "@errorReturnTrace",
        "@export",
        "@extern",
        "@fence",
        "@field",
        "@fieldParentPtr",
        "@floatCast",
        "@floatToInt",
        "@floor",
        "@frame",
        "@frameAddress",
        "@hasDecl",
        "@hasField",
        "@import",
        "@intCast",
        "@intToEnum",
        "@intToFloat",
        "@intToPtr",
        "@log",
        "@max",
        "@memcpy",
        "@memset",
        "@min",
        "@mod",
        "@mulAdd",
        "@mulWithOverflow",
        "@offsetOf",
        "@panic",
        "@popCount",
        "@ptrCast",
        "@ptrToInt",
        "@reduce",
        "@rem",
        "@returnAddress",
        "@round",
        "@setAlignStack",
        "@setCold",
        "@setEvalBranchQuota",
        "@setFloatMode",
        "@setRuntimeSafety",
        "@shlExact",
        "@shlWithOverflow",
        "@shrExact",
        "@shuffle",
        "@sizeOf",
        "@splat",
        "@sqrt",
        "@subWithOverflow",
        "@tagName",
        "@This",
        "@truncate",
        "@trunc",
        "@Type",
        "@typeInfo",
        "@typeName",
        "@TypeOf",
        "@Vector",
        "@wasmMemoryGrow",
        "@wasmMemorySize",
    }
)


class ZigStateMachineLexer(StateMachineLexer):
    """Zig lexer."""

    name = "zig"
    aliases = ()
    filenames = ("*.zig",)
    mimetypes = ("text/x-zig",)

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> Iterator[Token]:
        pos = start
        length = end if end is not None else len(code)
        line = 1
        line_start = start

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Whitespace
            if char in self.WHITESPACE:
                start = pos
                start_line = line
                while pos < length and code[pos] in self.WHITESPACE:
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start:pos], start_line, col)
                continue

            # Comments //
            if char == "/" and pos + 1 < length and code[pos + 1] == "/":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_SINGLE, code[start:pos], line, col)
                continue

            # Builtins @name
            if char == "@":
                start = pos
                pos += 1
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                word = code[start:pos]
                if word in _BUILTINS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Strings
            if char == '"':
                start = pos
                pos += 1
                pos, _ = scan_string(code, pos, '"')
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Character literals
            if char == "'":
                start = pos
                pos += 1
                if pos < length and code[pos] == "\\":
                    pos += 2
                elif pos < length:
                    pos += 1
                if pos < length and code[pos] == "'":
                    pos += 1
                yield Token(TokenType.STRING_CHAR, code[start:pos], line, col)
                continue

            # Multiline strings (start with \\)
            if char == "\\" and pos + 1 < length and code[pos + 1] == "\\":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS:
                start = pos
                if code[pos] == "0" and pos + 1 < length:
                    next_char = code[pos + 1]
                    if next_char in "xX":
                        pos += 2
                        while pos < length and (code[pos] in HEX_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_HEX, code[start:pos], line, col)
                        continue
                    if next_char in "oO":
                        pos += 2
                        while pos < length and (code[pos] in OCTAL_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_OCT, code[start:pos], line, col)
                        continue
                    if next_char in "bB":
                        pos += 2
                        while pos < length and (code[pos] in BINARY_DIGITS or code[pos] == "_"):
                            pos += 1
                        yield Token(TokenType.NUMBER_BIN, code[start:pos], line, col)
                        continue

                while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                    pos += 1
                is_float = False
                if (
                    pos < length
                    and code[pos] == "."
                    and pos + 1 < length
                    and code[pos + 1] in DIGITS
                ):
                    is_float = True
                    pos += 1
                    while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                        pos += 1
                if pos < length and code[pos] in "eEpP":
                    is_float = True
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and (code[pos] in DIGITS or code[pos] == "_"):
                        pos += 1
                yield Token(
                    TokenType.NUMBER_FLOAT if is_float else TokenType.NUMBER_INTEGER,
                    code[start:pos],
                    line,
                    col,
                )
                continue

            # Keywords and identifiers
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                word = code[start:pos]
                if word in _CONSTANTS:
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                elif word in ("fn", "struct", "enum", "union", "error", "const", "var"):
                    yield Token(TokenType.KEYWORD_DECLARATION, word, line, col)
                elif word in ("usingnamespace",):
                    yield Token(TokenType.KEYWORD_NAMESPACE, word, line, col)
                elif word in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif word in _TYPES:
                    yield Token(TokenType.KEYWORD_TYPE, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Operators
            if char in "=<>!&|+-*/%^~":
                start = pos
                if pos + 1 < length and code[pos : pos + 2] in (
                    "==",
                    "!=",
                    "<=",
                    ">=",
                    "&&",
                    "||",
                    "++",
                    "--",
                    "+=",
                    "-=",
                    "*=",
                    "/=",
                    "%=",
                    "&=",
                    "|=",
                    "^=",
                    "<<",
                    ">>",
                    ".*",
                    ".?",
                ):
                    pos += 2
                else:
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            # Punctuation
            if char in "()[]{}:;,.?":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1
