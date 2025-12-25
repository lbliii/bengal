"""Clojure lexer for Rosettes.

Thread-safe regex-based tokenizer for Clojure source code.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["ClojureLexer"]

_SPECIAL_FORMS = (
    "def",
    "defn",
    "defn-",
    "defmacro",
    "defmethod",
    "defmulti",
    "defonce",
    "defprotocol",
    "defrecord",
    "defstruct",
    "deftype",
    "fn",
    "if",
    "do",
    "let",
    "letfn",
    "quote",
    "var",
    "loop",
    "recur",
    "throw",
    "try",
    "catch",
    "finally",
    "monitor-enter",
    "monitor-exit",
    "new",
    "set!",
    ".",
    "..",
)

_DECLARATIONS = (
    "ns",
    "in-ns",
    "import",
    "use",
    "require",
    "refer",
)

_BUILTINS = (
    "agent",
    "atom",
    "await",
    "apply",
    "assoc",
    "comp",
    "complement",
    "concat",
    "conj",
    "cons",
    "constantly",
    "count",
    "cycle",
    "dec",
    "dissoc",
    "drop",
    "empty?",
    "every?",
    "filter",
    "first",
    "flatten",
    "fn?",
    "get",
    "get-in",
    "hash-map",
    "hash-set",
    "identity",
    "inc",
    "interleave",
    "interpose",
    "into",
    "iterate",
    "juxt",
    "keys",
    "last",
    "lazy-seq",
    "list",
    "list*",
    "map",
    "map-indexed",
    "mapcat",
    "max",
    "merge",
    "min",
    "nil?",
    "not",
    "not-any?",
    "not-empty",
    "not-every?",
    "nth",
    "partial",
    "partition",
    "peek",
    "pop",
    "print",
    "println",
    "prn",
    "range",
    "reduce",
    "reductions",
    "ref",
    "remove",
    "repeat",
    "repeatedly",
    "rest",
    "reverse",
    "second",
    "seq",
    "seq?",
    "set",
    "some",
    "sort",
    "sort-by",
    "split-at",
    "split-with",
    "str",
    "take",
    "take-while",
    "update",
    "update-in",
    "vals",
    "vec",
    "vector",
    "when",
    "when-not",
    "zero?",
    "zipmap",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in ("true", "false", "nil"):
        return TokenType.KEYWORD_CONSTANT
    if word in _SPECIAL_FORMS:
        if word.startswith("def"):
            return TokenType.KEYWORD_DECLARATION
        return TokenType.KEYWORD
    if word in _DECLARATIONS:
        return TokenType.KEYWORD_NAMESPACE
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class ClojureLexer(PatternLexer):
    """Clojure lexer. Thread-safe."""

    name = "clojure"
    aliases = ("clj", "edn")
    filenames = ("*.clj", "*.cljs", "*.cljc", "*.edn")
    mimetypes = ("text/x-clojure", "application/x-clojure")

    _WORD_PATTERN = r"[a-zA-Z_*+!\-?<>=][a-zA-Z0-9_*+!\-?<>=/.]*"

    rules = (
        # Comments
        Rule(re.compile(r";.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"#_\s*\S+"), TokenType.COMMENT_SINGLE),  # Discard
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Regex
        Rule(re.compile(r'#"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_REGEX),
        # Keywords
        Rule(re.compile(r":/?[a-zA-Z_*+!\-?<>=][a-zA-Z0-9_*+!\-?<>=/.]*"), TokenType.STRING_SYMBOL),
        # Characters
        Rule(
            re.compile(r"\\(?:newline|space|tab|backspace|formfeed|return|u[0-9a-fA-F]{4}|.)"),
            TokenType.STRING_CHAR,
        ),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F]+N?"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"0[0-7]+N?"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"\d+\.\d*(?:[eE][+-]?\d+)?M?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+/\d+"), TokenType.NUMBER),  # Ratio
        Rule(re.compile(r"\d+[rR][0-9a-zA-Z]+N?"), TokenType.NUMBER),  # Radix
        Rule(re.compile(r"\d+N?"), TokenType.NUMBER_INTEGER),
        # Reader macros
        Rule(re.compile(r"#'\S+"), TokenType.NAME_VARIABLE),  # Var quote
        Rule(re.compile(r"#\^\{"), TokenType.PUNCTUATION),  # Metadata
        Rule(re.compile(r"#\("), TokenType.PUNCTUATION),  # Anonymous fn
        Rule(re.compile(r"#\{"), TokenType.PUNCTUATION),  # Set
        Rule(re.compile(r"@"), TokenType.OPERATOR),  # Deref
        Rule(re.compile(r"'"), TokenType.OPERATOR),  # Quote
        Rule(re.compile(r"`"), TokenType.OPERATOR),  # Syntax quote
        Rule(re.compile(r"~@?"), TokenType.OPERATOR),  # Unquote
        # Symbols/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Punctuation
        Rule(re.compile(r"[()[\]{}^]"), TokenType.PUNCTUATION),
        # Whitespace (including commas)
        Rule(re.compile(r"[\s,]+"), TokenType.WHITESPACE),
    )
