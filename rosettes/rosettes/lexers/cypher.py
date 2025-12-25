"""Cypher (Neo4j) lexer for Rosettes.

Thread-safe regex-based tokenizer for Cypher graph query language.
"""

import re

from rosettes._types import TokenType
from rosettes.lexers._base import PatternLexer, Rule

__all__ = ["CypherLexer"]

# Cypher keywords (case-insensitive)
_KEYWORDS = frozenset(
    (
        # Clauses
        "match",
        "optional",
        "where",
        "with",
        "return",
        "order",
        "by",
        "skip",
        "limit",
        "create",
        "merge",
        "delete",
        "detach",
        "set",
        "remove",
        "foreach",
        "unwind",
        "union",
        "all",
        "call",
        "yield",
        # Sub-clauses
        "on",
        "case",
        "when",
        "then",
        "else",
        "end",
        "as",
        "distinct",
        "using",
        "index",
        "scan",
        "join",
        # Operators
        "and",
        "or",
        "not",
        "xor",
        "is",
        "in",
        "starts",
        "ends",
        "contains",
        "null",
        # Modifiers
        "asc",
        "ascending",
        "desc",
        "descending",
        # Node patterns
        "shortestpath",
        "allshortestpaths",
        # Other
        "constraint",
        "assert",
        "unique",
        "exists",
        "node",
        "relationship",
        "key",
        "drop",
        "load",
        "csv",
        "headers",
        "from",
        "fieldterminator",
        "periodic",
        "commit",
    )
)

# Cypher functions
_FUNCTIONS = frozenset(
    (
        # Aggregation
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "collect",
        "stdev",
        "stdevp",
        "percentilecont",
        "percentiledisc",
        # Scalar
        "id",
        "type",
        "labels",
        "keys",
        "properties",
        "head",
        "last",
        "size",
        "length",
        "coalesce",
        "timestamp",
        "tointeger",
        "tofloat",
        "tostring",
        "toboolean",
        # String
        "left",
        "right",
        "substring",
        "trim",
        "ltrim",
        "rtrim",
        "replace",
        "split",
        "reverse",
        "tolower",
        "toupper",
        # Math
        "abs",
        "ceil",
        "floor",
        "round",
        "sign",
        "rand",
        "log",
        "log10",
        "exp",
        "sqrt",
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "atan2",
        "pi",
        "e",
        # List
        "range",
        "reduce",
        "extract",
        "filter",
        "all",
        "any",
        "none",
        "single",
        # Path
        "nodes",
        "relationships",
        "startnode",
        "endnode",
        # Date/time
        "date",
        "time",
        "datetime",
        "localdatetime",
        "localtime",
        "duration",
    )
)


def _classify_word(match: re.Match[str]) -> TokenType:
    """Classify Cypher identifiers (case-insensitive)."""
    word = match.group(0).lower()
    if word in ("true", "false", "null"):
        return TokenType.KEYWORD_CONSTANT
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _FUNCTIONS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class CypherLexer(PatternLexer):
    """Cypher (Neo4j) lexer. Thread-safe."""

    name = "cypher"
    aliases = ("neo4j", "cql")
    filenames = ("*.cypher", "*.cql")
    mimetypes = ("application/x-cypher-query",)

    rules = (
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*.*?\*/", re.DOTALL), TokenType.COMMENT_MULTILINE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING_DOUBLE),
        Rule(re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), TokenType.STRING_SINGLE),
        # Parameters: $param
        Rule(re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),
        # Node labels: :Label
        Rule(re.compile(r":[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_LABEL),
        # Relationship types: -[:TYPE]->
        Rule(re.compile(r"-\["), TokenType.PUNCTUATION),
        Rule(re.compile(r"\]->?"), TokenType.PUNCTUATION),
        Rule(re.compile(r"<-"), TokenType.PUNCTUATION),
        # Properties: {key: value}
        Rule(re.compile(r"\{"), TokenType.PUNCTUATION),
        Rule(re.compile(r"\}"), TokenType.PUNCTUATION),
        # Node patterns: ()
        Rule(re.compile(r"\("), TokenType.PUNCTUATION),
        Rule(re.compile(r"\)"), TokenType.PUNCTUATION),
        # Numbers
        Rule(re.compile(r"-?\d+\.\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"-?\d+"), TokenType.NUMBER_INTEGER),
        # Operators
        Rule(re.compile(r"=~|<>|<=|>=|<|>|=|\+|-|\*|/|%"), TokenType.OPERATOR),
        # Range: ..
        Rule(re.compile(r"\.\."), TokenType.OPERATOR),
        # Dot access
        Rule(re.compile(r"\."), TokenType.PUNCTUATION),
        # Keywords and identifiers
        Rule(re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"), _classify_word),
        # Punctuation
        Rule(re.compile(r"[,:\[\]]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
