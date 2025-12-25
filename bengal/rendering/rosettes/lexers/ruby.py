"""Ruby lexer for Rosettes.

Thread-safe regex-based tokenizer for Ruby source code.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["RubyLexer"]

_KEYWORDS = (
    "alias",
    "and",
    "begin",
    "break",
    "case",
    "class",
    "def",
    "defined?",
    "do",
    "else",
    "elsif",
    "end",
    "ensure",
    "for",
    "if",
    "in",
    "module",
    "next",
    "not",
    "or",
    "redo",
    "rescue",
    "retry",
    "return",
    "self",
    "super",
    "then",
    "undef",
    "unless",
    "until",
    "when",
    "while",
    "yield",
    "__ENCODING__",
    "__FILE__",
    "__LINE__",
)

_CONSTANTS = ("true", "false", "nil")

_BUILTINS = (
    "puts",
    "print",
    "gets",
    "require",
    "require_relative",
    "include",
    "extend",
    "attr_reader",
    "attr_writer",
    "attr_accessor",
    "raise",
    "lambda",
    "proc",
    "loop",
    "each",
    "map",
    "select",
    "reject",
    "reduce",
    "inject",
    "find",
    "sort",
    "sort_by",
    "first",
    "last",
    "length",
    "size",
    "empty?",
    "any?",
    "all?",
    "none?",
    "one?",
    "to_s",
    "to_i",
    "to_f",
    "to_a",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word in ("class", "module", "def"):
        return TokenType.KEYWORD_DECLARATION
    if word in ("require", "require_relative", "include", "extend"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class RubyLexer(PatternLexer):
    """Ruby lexer. Thread-safe."""

    name = "ruby"
    aliases = ("rb",)
    filenames = ("*.rb", "*.rake", "*.gemspec", "Rakefile", "Gemfile")
    mimetypes = ("text/x-ruby",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*[?!]?\b"

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"^=begin[\s\S]*?^=end", re.MULTILINE), TokenType.COMMENT_MULTILINE),
        # Heredocs (simplified)
        Rule(re.compile(r"<<[-~]?'?(\w+)'?.*?\n[\s\S]*?\n\1"), TokenType.STRING_HEREDOC),
        # Regex
        Rule(re.compile(r"/(?:[^/\\]|\\.)+/[imxo]*"), TokenType.STRING_REGEX),
        # Strings
        Rule(re.compile(r"%[qQwWiIx]?\{[^}]*\}"), TokenType.STRING),
        Rule(re.compile(r"%[qQwWiIx]?\[[^\]]*\]"), TokenType.STRING),
        Rule(re.compile(r"%[qQwWiIx]?\([^)]*\)"), TokenType.STRING),
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Symbols
        Rule(re.compile(r":[a-zA-Z_][a-zA-Z0-9_]*[?!]?"), TokenType.STRING_SYMBOL),
        Rule(re.compile(r':"[^"]*"'), TokenType.STRING_SYMBOL),
        # Instance/class variables
        Rule(re.compile(r"@@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE_CLASS),
        Rule(re.compile(r"@[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE_INSTANCE),
        # Global variables
        Rule(
            re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*|\$[0-9!@&+`'=~/\\,;.<>*$?:\"]"),
            TokenType.NAME_VARIABLE_GLOBAL,
        ),
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
        Rule(re.compile(r"<=>|<<=|>>=|===|!~|=~|\.\.\.?"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<<|>>|\*\*"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|&&=|\|\|="), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%&|^!~<>=?:]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
