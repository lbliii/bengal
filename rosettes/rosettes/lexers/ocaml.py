"""OCaml lexer for Rosettes.

Thread-safe regex-based tokenizer for OCaml and ReasonML.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["OcamlLexer"]

# OCaml keywords
_KEYWORDS = frozenset(
    (
        "and",
        "as",
        "assert",
        "asr",
        "begin",
        "class",
        "constraint",
        "do",
        "done",
        "downto",
        "else",
        "end",
        "exception",
        "external",
        "for",
        "fun",
        "function",
        "functor",
        "if",
        "in",
        "include",
        "inherit",
        "initializer",
        "land",
        "lazy",
        "let",
        "lor",
        "lsl",
        "lsr",
        "lxor",
        "match",
        "method",
        "mod",
        "module",
        "mutable",
        "new",
        "nonrec",
        "object",
        "of",
        "open",
        "or",
        "private",
        "rec",
        "sig",
        "struct",
        "then",
        "to",
        "try",
        "type",
        "val",
        "virtual",
        "when",
        "while",
        "with",
    )
)

_BUILTINS = frozenset(
    (
        "true",
        "false",
        "Some",
        "None",
        "Ok",
        "Error",
        "ref",
        "not",
        "raise",
        "failwith",
        "invalid_arg",
        "ignore",
        "print_string",
        "print_endline",
        "print_int",
        "print_float",
        "print_char",
        "print_newline",
        "prerr_string",
        "prerr_endline",
        "exit",
    )
)

_TYPES = frozenset(
    (
        "int",
        "float",
        "bool",
        "char",
        "string",
        "bytes",
        "unit",
        "list",
        "array",
        "option",
        "result",
        "exn",
        "ref",
        "lazy_t",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify OCaml identifiers."""
    word = match.group(0)
    if word in ("true", "false"):
        return TokenType.KEYWORD_CONSTANT
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    # Capitalized = constructor or module
    if word[0].isupper():
        return TokenType.NAME_CLASS
    return TokenType.NAME


class OcamlLexer(PatternLexer):
    """OCaml lexer. Thread-safe."""

    name = "ocaml"
    aliases = ("ml", "reasonml", "reason", "rescript")
    filenames = ("*.ml", "*.mli", "*.mll", "*.mly", "*.re", "*.rei", "*.res", "*.resi")
    mimetypes = ("text/x-ocaml",)

    rules = (
        # Comments (nested)
        Rule(re.compile(r"\(\*.*?\*\)", re.DOTALL), TokenType.COMMENT_MULTILINE),
        # Doc comments
        Rule(re.compile(r"\(\*\*.*?\*\)", re.DOTALL), TokenType.STRING_DOC),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        # Characters
        Rule(
            re.compile(r"'(?:[^'\\]|\\(?:x[0-9a-fA-F]{2}|[0-3]?[0-7]{1,2}|[nrtb\\']))'"),
            TokenType.STRING_CHAR,
        ),
        # Labels: ~label and ?label
        Rule(re.compile(r"[~?][a-z_][a-zA-Z0-9_']*"), TokenType.NAME_LABEL),
        # Type variables: 'a, 'b
        Rule(re.compile(r"'[a-z][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),
        # Polymorphic variants: `Tag
        Rule(re.compile(r"`[A-Z][a-zA-Z0-9_]*"), TokenType.NAME_TAG),
        # Numbers
        Rule(re.compile(r"-?0[xX][0-9a-fA-F][0-9a-fA-F_]*"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"-?0[oO][0-7][0-7_]*"), TokenType.NUMBER_OCT),
        Rule(re.compile(r"-?0[bB][01][01_]*"), TokenType.NUMBER_BIN),
        Rule(re.compile(r"-?\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d[\d_]*[eE][+-]?\d[\d_]*"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d[\d_]*"), TokenType.NUMBER_INTEGER),
        # Operators
        Rule(re.compile(r"->|<-|:=|::|\|>|@@|@|>>|<<|&&|\|\||::|;;"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/=<>@^|&!]+"), TokenType.OPERATOR),
        # Keywords and identifiers
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_']*\b"), _classify_word),
        # Punctuation
        Rule(re.compile(r"[(){}\[\];:,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
