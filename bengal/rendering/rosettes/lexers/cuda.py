"""CUDA lexer for Rosettes.

Thread-safe regex-based tokenizer for NVIDIA CUDA source code.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["CudaLexer"]

# C/C++ keywords plus CUDA-specific
_KEYWORDS = (
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
    # CUDA-specific
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
)

_TYPES = (
    # C/C++ types
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
    # CUDA types
    "dim3",
    "cudaError_t",
    "cudaStream_t",
    "cudaEvent_t",
    "cudaDeviceProp",
    "cudaMemcpyKind",
    "cudaFuncCache",
    "cudaSharedMemConfig",
    # CUDA vector types
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
    "long1",
    "long2",
    "long3",
    "long4",
    "ulong1",
    "ulong2",
    "ulong3",
    "ulong4",
    "float1",
    "float2",
    "float3",
    "float4",
    "double1",
    "double2",
    "double3",
    "double4",
    "longlong1",
    "longlong2",
    "ulonglong1",
    "ulonglong2",
    # Half precision
    "half",
    "half2",
    "__half",
    "__half2",
)

_BUILTINS = (
    # CUDA built-in variables
    "threadIdx",
    "blockIdx",
    "blockDim",
    "gridDim",
    "warpSize",
    # CUDA functions
    "__syncthreads",
    "__syncthreads_count",
    "__syncthreads_and",
    "__syncthreads_or",
    "__syncwarp",
    "__threadfence",
    "__threadfence_block",
    "__threadfence_system",
    "atomicAdd",
    "atomicSub",
    "atomicExch",
    "atomicMin",
    "atomicMax",
    "atomicInc",
    "atomicDec",
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
    "__ldcs",
    "__ldca",
    "__ldcg",
    "__ldcv",
    # Math functions
    "__sinf",
    "__cosf",
    "__tanf",
    "__expf",
    "__logf",
    "__powf",
    "__sqrtf",
    "__rsqrtf",
    "__fmaf",
    "__fdividef",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("true", "false", "nullptr", "NULL"):
        return TokenType.KEYWORD_CONSTANT
    if word.startswith("__") and word.endswith("__"):
        return TokenType.KEYWORD  # CUDA qualifiers
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
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class CudaLexer(PatternLexer):
    """CUDA lexer. Thread-safe."""

    name = "cuda"
    aliases = ("cu",)
    filenames = ("*.cu", "*.cuh")
    mimetypes = ("text/x-cuda",)

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
        # Kernel launch syntax
        Rule(re.compile(r"<<<"), TokenType.PUNCTUATION),
        Rule(re.compile(r">>>"), TokenType.PUNCTUATION),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Characters
        Rule(re.compile(r"'[^'\\]'|'\\.'|'\\x[0-9a-fA-F]{1,2}'"), TokenType.STRING_CHAR),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F]+[uUlL]*"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[bB][01]+[uUlL]*"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"\d+\.\d*(?:[eE][+-]?\d+)?[fFlL]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\.\d+(?:[eE][+-]?\d+)?[fFlL]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[eE][+-]?\d+[fFlL]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[uUlLfF]*"), TokenType.NUMBER_INTEGER),
        # CUDA qualifiers (must come before general keywords)
        Rule(
            re.compile(
                r"__(?:global|device|host|constant|shared|managed|restrict|noinline|forceinline|launch_bounds|grid_constant)__"
            ),
            TokenType.KEYWORD,
        ),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"->|::|\+\+|--"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<<|>>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!~<>=?:]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
