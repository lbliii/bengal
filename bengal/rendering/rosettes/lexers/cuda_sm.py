"""Hand-written CUDA lexer using composable scanner mixins.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    IDENT_START,
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    NumberConfig,
    OperatorConfig,
    scan_identifier,
    scan_line_comment,
    scan_string,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["CudaStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
        # C/C++ keywords
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
        "class",
        "namespace",
        "template",
        "typename",
        "using",
        "virtual",
        "public",
        "private",
        "protected",
        "new",
        "delete",
        "this",
        "throw",
        "try",
        "catch",
        "const_cast",
        "dynamic_cast",
        "reinterpret_cast",
        "static_cast",
        # CUDA qualifiers
        "__global__",
        "__device__",
        "__host__",
        "__constant__",
        "__shared__",
        "__managed__",
        "__restrict__",
        "__noinline__",
        "__forceinline__",
        "__launch_bounds__",
        "__grid_constant__",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "void",
        "char",
        "short",
        "int",
        "long",
        "float",
        "double",
        "signed",
        "unsigned",
        "bool",
        "size_t",
        "ptrdiff_t",
        "dim3",
        "cudaError_t",
        "cudaStream_t",
        "cudaEvent_t",
        "cudaDeviceProp",
        # Vector types
        "char1",
        "char2",
        "char3",
        "char4",
        "uchar1",
        "uchar2",
        "uchar3",
        "uchar4",
        "short1",
        "short2",
        "short3",
        "short4",
        "ushort1",
        "ushort2",
        "ushort3",
        "ushort4",
        "int1",
        "int2",
        "int3",
        "int4",
        "uint1",
        "uint2",
        "uint3",
        "uint4",
        "float1",
        "float2",
        "float3",
        "float4",
        "double1",
        "double2",
        "double3",
        "double4",
        "half",
        "half2",
        "__half",
        "__half2",
    }
)

_BUILTINS: frozenset[str] = frozenset(
    {
        "threadIdx",
        "blockIdx",
        "blockDim",
        "gridDim",
        "warpSize",
        "__syncthreads",
        "__syncwarp",
        "__threadfence",
        "__threadfence_block",
        "atomicAdd",
        "atomicSub",
        "atomicExch",
        "atomicMin",
        "atomicMax",
        "atomicCAS",
        "atomicAnd",
        "atomicOr",
        "atomicXor",
        "__ballot_sync",
        "__all_sync",
        "__any_sync",
        "__shfl_sync",
        "__shfl_up_sync",
        "__shfl_down_sync",
        "__shfl_xor_sync",
        "__ldg",
    }
)

_CONSTANTS: frozenset[str] = frozenset({"true", "false", "nullptr", "NULL"})


class CudaStateMachineLexer(
    CStyleCommentsMixin,
    CStyleNumbersMixin,
    CStyleOperatorsMixin,
    StateMachineLexer,
):
    """CUDA lexer using composable mixins."""

    name = "cuda"
    aliases = ("cu",)
    filenames = ("*.cu", "*.cuh")
    mimetypes = ("text/x-cuda",)

    NUMBER_CONFIG = NumberConfig(
        integer_suffixes=("u", "U", "l", "L", "ul", "UL", "ll", "LL", "ull", "ULL"),
        float_suffixes=("f", "F", "l", "L"),
    )

    OPERATOR_CONFIG = OperatorConfig(
        three_char=frozenset({"...", ">>=", "<<=", "<<<", ">>>"}),
        two_char=frozenset(
            {
                "->",
                "::",
                "++",
                "--",
                "&&",
                "||",
                "==",
                "!=",
                "<=",
                ">=",
                "<<",
                ">>",
                "+=",
                "-=",
                "*=",
                "/=",
                "%=",
                "&=",
                "|=",
                "^=",
            }
        ),
        one_char=frozenset("+-*/%&|^~!<>=?:"),
    )

    def tokenize(self, code: str) -> Iterator[Token]:
        pos = 0
        length = len(code)
        line = 1
        line_start = 0

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

            # Preprocessor
            if char == "#":
                start = pos
                pos = scan_line_comment(code, pos)
                yield Token(TokenType.COMMENT_PREPROC, code[start:pos], line, col)
                continue

            # Comments
            token, new_pos = self._try_comment(code, pos, line, col)
            if token:
                if token.type == TokenType.COMMENT_MULTILINE:
                    newlines = token.value.count("\n")
                    if newlines:
                        line += newlines
                        line_start = pos + token.value.rfind("\n") + 1
                yield token
                pos = new_pos
                continue

            # Kernel launch syntax <<< >>>
            if char == "<" and code[pos : pos + 3] == "<<<":
                yield Token(TokenType.PUNCTUATION, "<<<", line, col)
                pos += 3
                continue
            if char == ">" and code[pos : pos + 3] == ">>>":
                yield Token(TokenType.PUNCTUATION, ">>>", line, col)
                pos += 3
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
                pos, _ = scan_string(code, pos, "'")
                yield Token(TokenType.STRING_CHAR, code[start:pos], line, col)
                continue

            # Numbers
            token, new_pos = self._try_number(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Identifiers (including CUDA qualifiers with __)
            if char in IDENT_START or char == "_":
                start = pos
                pos = scan_identifier(code, pos)
                word = code[start:pos]
                token_type = self._classify_word(word)
                yield Token(token_type, word, line, col)
                continue

            # Operators
            token, new_pos = self._try_operator(code, pos, line, col)
            if token:
                yield token
                pos = new_pos
                continue

            # Punctuation
            if char in "()[]{}:;,.":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1

    def _classify_word(self, word: str) -> TokenType:
        if word in _CONSTANTS:
            return TokenType.KEYWORD_CONSTANT
        if word.startswith("__") and word.endswith("__"):
            return TokenType.KEYWORD
        if word in ("struct", "class", "enum", "union", "typedef", "namespace"):
            return TokenType.KEYWORD_DECLARATION
        if word in ("using", "namespace"):
            return TokenType.KEYWORD_NAMESPACE
        if word in _KEYWORDS:
            return TokenType.KEYWORD
        if word in _TYPES:
            return TokenType.KEYWORD_TYPE
        if word in _BUILTINS:
            return TokenType.NAME_BUILTIN
        if word and word[0].isupper():
            return TokenType.NAME_CLASS
        return TokenType.NAME
