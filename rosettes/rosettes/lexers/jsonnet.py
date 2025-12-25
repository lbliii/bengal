"""Jsonnet lexer for Rosettes.

Thread-safe regex-based tokenizer for Jsonnet configuration language.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["JsonnetLexer"]

# Jsonnet keywords
_KEYWORDS = frozenset(
    (
        "assert",
        "else",
        "error",
        "false",
        "for",
        "function",
        "if",
        "import",
        "importstr",
        "importbin",
        "in",
        "local",
        "null",
        "self",
        "super",
        "tailstrict",
        "then",
        "true",
    )
)

# Jsonnet stdlib functions
_STDLIB = frozenset(
    (
        "std",
        "extVar",
        "type",
        "length",
        "get",
        "objectHas",
        "objectFields",
        "objectFieldsAll",
        "objectHasAll",
        "prune",
        "mapWithKey",
        "flatMap",
        "filter",
        "foldl",
        "foldr",
        "range",
        "repeat",
        "slice",
        "member",
        "count",
        "find",
        "map",
        "filterMap",
        "flattenArrays",
        "manifestIni",
        "manifestPython",
        "manifestPythonVars",
        "manifestJsonEx",
        "manifestYamlDoc",
        "manifestYamlStream",
        "manifestXmlJsonml",
        "manifestTomlEx",
        "makeArray",
        "format",
        "escapeStringBash",
        "escapeStringDollars",
        "escapeStringJson",
        "escapeStringPython",
        "parseInt",
        "parseOctal",
        "parseHex",
        "parseJson",
        "parseYaml",
        "encodeUTF8",
        "decodeUTF8",
        "md5",
        "sha1",
        "sha256",
        "sha512",
        "sha3",
        "base64",
        "base64Decode",
        "base64DecodeBytes",
        "sort",
        "uniq",
        "set",
        "setInter",
        "setUnion",
        "setDiff",
        "setMember",
        "split",
        "splitLimit",
        "strReplace",
        "asciiUpper",
        "asciiLower",
        "stringChars",
        "substr",
        "startsWith",
        "endsWith",
        "stripChars",
        "lstripChars",
        "rstripChars",
        "join",
        "lines",
        "toString",
        "codepoint",
        "char",
        "trace",
        "isString",
        "isNumber",
        "isBoolean",
        "isObject",
        "isArray",
        "isFunction",
        "ceil",
        "floor",
        "sqrt",
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "log",
        "exp",
        "pow",
        "modulo",
        "min",
        "max",
        "clamp",
        "abs",
        "sign",
        "avg",
        "sum",
        "xor",
        "xnor",
        "round",
        "isEmpty",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify Jsonnet identifiers."""
    word = match.group(0)
    if word in ("true", "false", "null"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("self", "super", "$"):
        return TokenType.KEYWORD_PSEUDO
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _STDLIB:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class JsonnetLexer(PatternLexer):
    """Jsonnet lexer. Thread-safe."""

    name = "jsonnet"
    aliases = ("libsonnet",)
    filenames = ("*.jsonnet", "*.libsonnet")
    mimetypes = ("application/jsonnet", "text/x-jsonnet")

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*.*?\*/", re.DOTALL), TokenType.COMMENT_MULTILINE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Text blocks (|||)
        Rule(re.compile(r"\|\|\|[\s\S]*?\|\|\|"), TokenType.STRING_HEREDOC),
        # Verbatim strings: @"..."
        Rule(re.compile(r'@"[^"]*"'), TokenType.STRING_OTHER),
        Rule(re.compile(r"@'[^']*'"), TokenType.STRING_OTHER),
        # Numbers
        Rule(re.compile(r"-?\d+\.\d+(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d+[eE][+-]?\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d+"), TokenType.NUMBER_INTEGER),
        # Object comprehension: [for ...], {[for ...]}
        Rule(re.compile(r"\[for\b"), TokenType.KEYWORD),
        # Dollar (special self)
        Rule(re.compile(r"\$"), TokenType.KEYWORD_PSEUDO),
        # Operators
        Rule(re.compile(r"\+:|\+{1,3}|==|!=|<=|>=|<<|>>|&&|\|\||<:|:>"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%<>=!&|^~]"), TokenType.OPERATOR),
        # Keywords and identifiers
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"), _classify_word),
        # Punctuation
        Rule(re.compile(r"[{}\[\]():;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
