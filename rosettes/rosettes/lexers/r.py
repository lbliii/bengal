"""R lexer for Rosettes.

Thread-safe regex-based tokenizer for R source code.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["RLexer"]

_KEYWORDS = (
    "break",
    "else",
    "for",
    "function",
    "if",
    "in",
    "next",
    "repeat",
    "return",
    "while",
)

_CONSTANTS = (
    "TRUE",
    "FALSE",
    "NA",
    "NA_integer_",
    "NA_real_",
    "NA_complex_",
    "NA_character_",
    "NULL",
    "Inf",
    "NaN",
)

_BUILTINS = (
    "abs",
    "acos",
    "acosh",
    "all",
    "any",
    "append",
    "apply",
    "args",
    "asin",
    "asinh",
    "atan",
    "atan2",
    "atanh",
    "attr",
    "attributes",
    "c",
    "cat",
    "cbind",
    "ceiling",
    "character",
    "class",
    "colnames",
    "complex",
    "cos",
    "cosh",
    "cummax",
    "cummin",
    "cumprod",
    "cumsum",
    "data.frame",
    "det",
    "diag",
    "diff",
    "dim",
    "double",
    "eigen",
    "exp",
    "floor",
    "function",
    "grep",
    "grepl",
    "gsub",
    "head",
    "identical",
    "ifelse",
    "integer",
    "is.character",
    "is.data.frame",
    "is.list",
    "is.na",
    "is.null",
    "is.numeric",
    "is.vector",
    "lapply",
    "length",
    "library",
    "list",
    "log",
    "log10",
    "log2",
    "logical",
    "ls",
    "mapply",
    "match",
    "matrix",
    "max",
    "mean",
    "merge",
    "min",
    "names",
    "nchar",
    "ncol",
    "nrow",
    "numeric",
    "order",
    "paste",
    "paste0",
    "print",
    "prod",
    "range",
    "rank",
    "rbind",
    "read.csv",
    "read.table",
    "rep",
    "require",
    "return",
    "rev",
    "rm",
    "round",
    "rownames",
    "sample",
    "sapply",
    "sd",
    "seq",
    "setdiff",
    "setwd",
    "sin",
    "sinh",
    "sort",
    "split",
    "sprintf",
    "sqrt",
    "stop",
    "str",
    "strsplit",
    "sub",
    "substr",
    "sum",
    "summary",
    "t",
    "table",
    "tail",
    "tan",
    "tanh",
    "tolower",
    "toupper",
    "typeof",
    "unique",
    "unlist",
    "var",
    "vector",
    "warning",
    "which",
    "write.csv",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _CONSTANTS:
        return TokenType.KEYWORD_CONSTANT
    if word == "function":
        return TokenType.KEYWORD_DECLARATION
    if word in ("library", "require"):
        return TokenType.KEYWORD_NAMESPACE
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _BUILTINS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class RLexer(PatternLexer):
    """R lexer. Thread-safe."""

    name = "r"
    aliases = ("rlang", "splus")
    filenames = ("*.r", "*.R", "*.Rhistory", "*.Rprofile")
    mimetypes = ("text/x-r",)

    _WORD_PATTERN = r"\b[a-zA-Z_.][a-zA-Z0-9_.]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Raw strings (R 4.0+)
        Rule(re.compile(r'r"[^"]*"'), TokenType.STRING),
        Rule(re.compile(r"r'[^']*'"), TokenType.STRING),
        # Numbers
        Rule(re.compile(r"0[xX][0-9a-fA-F]+[Li]?"), TokenType.NUMBER_HEX),
        Rule(re.compile(r"\d+\.\d*(?:[eE][+-]?\d+)?[Li]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\.\d+(?:[eE][+-]?\d+)?[Li]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[eE][+-]?\d+[Li]?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[Li]?"), TokenType.NUMBER_INTEGER),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Assignment operators
        Rule(re.compile(r"<<?-|->?>?|<<-"), TokenType.OPERATOR),
        # Operators
        Rule(re.compile(r"%%|%/%|%\*%|%in%|%o%|%x%"), TokenType.OPERATOR),
        Rule(re.compile(r"&&?|\|\|?|==|!=|<=?|>=?"), TokenType.OPERATOR),
        Rule(re.compile(r"\+|-|\*|/|\^|~|!|@|\$|:"), TokenType.OPERATOR),
        Rule(re.compile(r"="), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{},;]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
