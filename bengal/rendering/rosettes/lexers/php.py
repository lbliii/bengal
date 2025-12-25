"""PHP lexer for Rosettes.

Thread-safe regex-based tokenizer for PHP source code.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["PhpLexer"]

_KEYWORDS = (
    "abstract",
    "and",
    "array",
    "as",
    "break",
    "callable",
    "case",
    "catch",
    "class",
    "clone",
    "const",
    "continue",
    "declare",
    "default",
    "die",
    "do",
    "echo",
    "else",
    "elseif",
    "empty",
    "enddeclare",
    "endfor",
    "endforeach",
    "endif",
    "endswitch",
    "endwhile",
    "eval",
    "exit",
    "extends",
    "final",
    "finally",
    "fn",
    "for",
    "foreach",
    "function",
    "global",
    "goto",
    "if",
    "implements",
    "include",
    "include_once",
    "instanceof",
    "insteadof",
    "interface",
    "isset",
    "list",
    "match",
    "namespace",
    "new",
    "or",
    "print",
    "private",
    "protected",
    "public",
    "readonly",
    "require",
    "require_once",
    "return",
    "static",
    "switch",
    "throw",
    "trait",
    "try",
    "unset",
    "use",
    "var",
    "while",
    "xor",
    "yield",
    "yield from",
)

_CONSTANTS = ("true", "false", "null", "TRUE", "FALSE", "NULL")

_TYPES = (
    "array",
    "bool",
    "boolean",
    "callable",
    "float",
    "int",
    "integer",
    "iterable",
    "mixed",
    "never",
    "null",
    "object",
    "resource",
    "string",
    "void",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    lower = word.lower()
    if lower in ("true", "false", "null"):
        return TokenType.KEYWORD_CONSTANT
    if lower in ("class", "interface", "trait", "function", "const", "enum"):
        return TokenType.KEYWORD_DECLARATION
    if lower in ("namespace", "use", "require", "require_once", "include", "include_once"):
        return TokenType.KEYWORD_NAMESPACE
    if lower in _TYPES:
        return TokenType.KEYWORD_TYPE
    if lower in _KEYWORDS:
        return TokenType.KEYWORD
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class PhpLexer(PatternLexer):
    """PHP lexer. Thread-safe."""

    name = "php"
    aliases = ("php3", "php4", "php5", "php7", "php8")
    filenames = ("*.php", "*.php3", "*.php4", "*.php5", "*.phtml")
    mimetypes = ("text/x-php", "application/x-php")

    _WORD_PATTERN = r"\b[a-zA-Z_\x80-\xff][a-zA-Z0-9_\x80-\xff]*\b"

    rules = (
        # PHP tags
        Rule(re.compile(r"<\?(?:php)?|\?>"), TokenType.COMMENT_PREPROC),
        # Comments
        Rule(re.compile(r"//.*$|#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*\*[\s\S]*?\*/"), TokenType.STRING_DOC),  # PHPDoc
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Heredoc/Nowdoc
        Rule(re.compile(r"<<<'?(\w+)'?\n[\s\S]*?\n\1;?"), TokenType.STRING_HEREDOC),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Variables
        Rule(re.compile(r"\$[a-zA-Z_\x80-\xff][a-zA-Z0-9_\x80-\xff]*"), TokenType.NAME_VARIABLE),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F_]+"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[bB][01_]+"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"0[oO][0-7_]+"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*[eE][+-]?\d[\d_]*"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d[\d_]*"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"=>|->|\?\?|::|\.\.\.|<=>|\*\*"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|===|!=|!==|<=|>=|<>|<<|>>"), TokenType.OPERATOR),
        Rule(
            re.compile(r"\?\?=|\+=|-=|\*=|/=|\.=|%=|&=|\|=|\^=|<<=|>>=|\*\*="), TokenType.OPERATOR
        ),
        Rule(re.compile(r"[+\-*/%&|^!~<>=?:@.]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,\\]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
