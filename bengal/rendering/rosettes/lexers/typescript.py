"""TypeScript lexer for Rosettes.

Thread-safe regex-based tokenizer for TypeScript source code.
Extends JavaScript lexer with type annotations.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["TypeScriptLexer"]

# TypeScript keywords (includes JavaScript + type-specific)
_KEYWORDS = (
    # JavaScript keywords
    "async",
    "await",
    "break",
    "case",
    "catch",
    "class",
    "const",
    "continue",
    "debugger",
    "default",
    "delete",
    "do",
    "else",
    "export",
    "extends",
    "finally",
    "for",
    "function",
    "if",
    "import",
    "in",
    "instanceof",
    "let",
    "new",
    "of",
    "return",
    "static",
    "super",
    "switch",
    "this",
    "throw",
    "try",
    "typeof",
    "var",
    "void",
    "while",
    "with",
    "yield",
    # TypeScript-specific
    "abstract",
    "as",
    "asserts",
    "declare",
    "enum",
    "implements",
    "interface",
    "is",
    "keyof",
    "namespace",
    "override",
    "private",
    "protected",
    "public",
    "readonly",
    "type",
    "infer",
    "satisfies",
)

# Type keywords
_TYPE_KEYWORDS = (
    "any",
    "boolean",
    "never",
    "null",
    "number",
    "object",
    "string",
    "symbol",
    "undefined",
    "unknown",
    "void",
    "bigint",
)

# Built-in constants
_CONSTANTS = (
    "true",
    "false",
    "null",
    "undefined",
    "NaN",
    "Infinity",
)

# Built-in objects/functions
_BUILTINS = (
    "Array",
    "Boolean",
    "Date",
    "Error",
    "Function",
    "JSON",
    "Map",
    "Math",
    "Number",
    "Object",
    "Promise",
    "Proxy",
    "Record",
    "RegExp",
    "Set",
    "String",
    "Symbol",
    "WeakMap",
    "WeakSet",
    "Partial",
    "Required",
    "Readonly",
    "Pick",
    "Omit",
    "Exclude",
    "Extract",
    "NonNullable",
    "Parameters",
    "ReturnType",
    "InstanceType",
    "console",
    "document",
    "window",
    "globalThis",
)


def _classify_keyword(match: re.Match[str]) -> TokenType:
    """Classify a keyword match into the appropriate token type."""
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in _TYPE_KEYWORDS:
        return TokenType.KEYWORD_TYPE
    if word in ("function", "class", "const", "let", "var", "type", "interface", "enum"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "export", "from", "namespace"):
        return TokenType.KEYWORD_NAMESPACE
    return TokenType.KEYWORD


def _classify_name(match: re.Match[str]) -> TokenType:
    """Classify a name match into the appropriate token type."""
    word = match.group(0)
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class TypeScriptLexer(PatternLexer):
    """TypeScript lexer.

    Handles TypeScript syntax including type annotations, generics,
    interfaces, and decorators.
    Thread-safe: all state is immutable.
    """

    name = "typescript"
    aliases = ("ts",)
    filenames = ("*.ts", "*.tsx", "*.mts", "*.cts")
    mimetypes = ("text/typescript", "application/typescript")

    # Pattern for keywords
    _KEYWORD_PATTERN = r"\b(?:" + "|".join(_KEYWORDS + _CONSTANTS + _TYPE_KEYWORDS) + r")\b"

    # Pattern for identifiers
    _NAME_PATTERN = r"\b[a-zA-Z_$][a-zA-Z0-9_$]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Decorators
        Rule(re.compile(r"@[a-zA-Z_$][a-zA-Z0-9_$]*"), TokenType.NAME_DECORATOR),
        # Template literals
        Rule(re.compile(r"`[^`\\]*(?:\\.[^`\\]*)*`"), TokenType.STRING),
        # Regular expressions
        Rule(re.compile(r"/(?!\*)(?:[^/\\]|\\.)+/[gimsuvy]*"), TokenType.STRING_REGEX),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+n?"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[oO][0-7_]+n?"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"0[bB][01_]+n?"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"\d[\d_]*\.[\d_]*(?:[eE][+-]?[\d_]+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\.[\d_]+(?:[eE][+-]?[\d_]+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?[\d_]+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*n"), TokenType.NUMBER_INTEGER),
        Rule(re.compile(r"\d[\d_]*"), TokenType.NUMBER_INTEGER),
        # Keywords
        Rule(re.compile(_KEYWORD_PATTERN), _classify_keyword),
        # Names
        Rule(re.compile(_NAME_PATTERN), _classify_name),
        # Arrow function
        Rule(re.compile(r"=>"), TokenType.OPERATOR),
        # Spread/rest
        Rule(re.compile(r"\.\.\."), TokenType.OPERATOR),
        # Type operators
        Rule(re.compile(r"\?\."), TokenType.OPERATOR),  # Optional chaining
        Rule(re.compile(r"!\."), TokenType.OPERATOR),  # Non-null assertion
        # Comparison and logical
        Rule(re.compile(r"===|!==|==|!=|<=|>=|<|>"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||\?\?"), TokenType.OPERATOR),
        # Assignment
        Rule(re.compile(r"\?\?=|\|\|=|&&="), TokenType.OPERATOR),
        Rule(re.compile(r"\*\*=|\+=|-=|\*=|/=|%=|&=|\|=|\^=|>>=|<<=|>>>="), TokenType.OPERATOR),
        # Other operators
        Rule(re.compile(r"\+\+|--"), TokenType.OPERATOR),
        Rule(re.compile(r"\*\*"), TokenType.OPERATOR),
        Rule(re.compile(r">>>|>>|<<"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^~!?:]"), TokenType.OPERATOR),
        # Punctuation (includes angle brackets for generics)
        Rule(re.compile(r"[()[\]{},.;<>]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
