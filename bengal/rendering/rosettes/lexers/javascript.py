"""JavaScript lexer for Rosettes.

Thread-safe regex-based tokenizer for JavaScript/ECMAScript source code.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["JavaScriptLexer"]

# JavaScript keywords
_KEYWORDS = (
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
)

# Reserved words / future keywords
_RESERVED = (
    "enum",
    "implements",
    "interface",
    "package",
    "private",
    "protected",
    "public",
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
    "Math",
    "Number",
    "Object",
    "Promise",
    "Proxy",
    "RegExp",
    "String",
    "Symbol",
    "console",
    "document",
    "window",
    "globalThis",
    "parseInt",
    "parseFloat",
    "isNaN",
    "isFinite",
    "encodeURI",
    "decodeURI",
    "encodeURIComponent",
    "decodeURIComponent",
    "setTimeout",
    "setInterval",
    "clearTimeout",
    "clearInterval",
    "fetch",
    "require",
    "module",
    "exports",
)


def _classify_keyword(match: re.Match[str]) -> TokenType:
    """Classify a keyword match into the appropriate token type."""
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in ("function", "class", "const", "let", "var"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("import", "export", "from"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _RESERVED:
        return TokenType.KEYWORD_RESERVED
    return TokenType.KEYWORD


def _classify_name(match: re.Match[str]) -> TokenType:
    """Classify a name match into the appropriate token type."""
    word = match.group(0)
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class JavaScriptLexer(PatternLexer):
    """JavaScript/ECMAScript lexer.

    Handles ES6+ syntax including arrow functions, template literals,
    destructuring, and async/await.
    Thread-safe: all state is immutable.
    """

    name = "javascript"
    aliases = ("js", "ecmascript")
    filenames = ("*.js", "*.mjs", "*.cjs")
    mimetypes = ("text/javascript", "application/javascript")

    # Pattern for keywords and constants
    _KEYWORD_PATTERN = r"\b(?:" + "|".join(_KEYWORDS + _CONSTANTS + _RESERVED) + r")\b"

    # Pattern for identifiers
    _NAME_PATTERN = r"\b[a-zA-Z_$][a-zA-Z0-9_$]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Template literals (simplified - no interpolation highlighting)
        Rule(re.compile(r"`[^`\\]*(?:\\.[^`\\]*)*`"), TokenType.STRING),
        # Regular expressions (simplified)
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
        Rule(re.compile(r"\d[\d_]*n"), TokenType.NUMBER_INTEGER),  # BigInt
        Rule(re.compile(r"\d[\d_]*"), TokenType.NUMBER_INTEGER),
        # Keywords (before names)
        Rule(re.compile(_KEYWORD_PATTERN), _classify_keyword),
        # Names
        Rule(re.compile(_NAME_PATTERN), _classify_name),
        # Arrow function
        Rule(re.compile(r"=>"), TokenType.OPERATOR),
        # Spread/rest
        Rule(re.compile(r"\.\.\."), TokenType.OPERATOR),
        # Comparison and logical operators
        Rule(re.compile(r"===|!==|==|!=|<=|>=|<|>"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||\?\?"), TokenType.OPERATOR),
        # Assignment operators
        Rule(re.compile(r"\?\?=|\|\|=|&&="), TokenType.OPERATOR),
        Rule(re.compile(r"\*\*=|\+=|-=|\*=|/=|%=|&=|\|=|\^=|>>=|<<=|>>>="), TokenType.OPERATOR),
        # Other operators
        Rule(re.compile(r"\+\+|--"), TokenType.OPERATOR),
        Rule(re.compile(r"\*\*"), TokenType.OPERATOR),
        Rule(re.compile(r">>>|>>|<<"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^~!?:]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{},.;]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
