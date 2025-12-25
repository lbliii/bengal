"""SQL lexer for Rosettes.

Thread-safe regex-based tokenizer for SQL queries.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["SqlLexer"]

_KEYWORDS = (
    "ADD",
    "ALL",
    "ALTER",
    "AND",
    "AS",
    "ASC",
    "BETWEEN",
    "BY",
    "CASE",
    "CHECK",
    "COLUMN",
    "CONSTRAINT",
    "CREATE",
    "DATABASE",
    "DEFAULT",
    "DELETE",
    "DESC",
    "DISTINCT",
    "DROP",
    "ELSE",
    "END",
    "EXISTS",
    "FALSE",
    "FOREIGN",
    "FROM",
    "FULL",
    "GROUP",
    "HAVING",
    "IF",
    "IN",
    "INDEX",
    "INNER",
    "INSERT",
    "INTO",
    "IS",
    "JOIN",
    "KEY",
    "LEFT",
    "LIKE",
    "LIMIT",
    "NOT",
    "NULL",
    "ON",
    "OR",
    "ORDER",
    "OUTER",
    "PRIMARY",
    "REFERENCES",
    "RIGHT",
    "SELECT",
    "SET",
    "TABLE",
    "THEN",
    "TRUE",
    "UNION",
    "UNIQUE",
    "UPDATE",
    "VALUES",
    "VIEW",
    "WHEN",
    "WHERE",
    "WITH",
)

_TYPES = (
    "BIGINT",
    "BINARY",
    "BIT",
    "BLOB",
    "BOOLEAN",
    "CHAR",
    "DATE",
    "DATETIME",
    "DECIMAL",
    "DOUBLE",
    "ENUM",
    "FLOAT",
    "INT",
    "INTEGER",
    "JSON",
    "LONGBLOB",
    "LONGTEXT",
    "MEDIUMBLOB",
    "MEDIUMINT",
    "MEDIUMTEXT",
    "NUMERIC",
    "REAL",
    "SET",
    "SMALLINT",
    "TEXT",
    "TIME",
    "TIMESTAMP",
    "TINYBLOB",
    "TINYINT",
    "TINYTEXT",
    "UUID",
    "VARBINARY",
    "VARCHAR",
    "YEAR",
)

_FUNCTIONS = (
    "ABS",
    "AVG",
    "CAST",
    "COALESCE",
    "CONCAT",
    "COUNT",
    "CURDATE",
    "CURTIME",
    "DATE",
    "DATEDIFF",
    "DAY",
    "EXTRACT",
    "FLOOR",
    "HOUR",
    "IFNULL",
    "INSTR",
    "ISNULL",
    "LEFT",
    "LENGTH",
    "LOWER",
    "LTRIM",
    "MAX",
    "MIN",
    "MINUTE",
    "MONTH",
    "NOW",
    "NULLIF",
    "REPLACE",
    "REVERSE",
    "RIGHT",
    "ROUND",
    "RTRIM",
    "SECOND",
    "SQRT",
    "SUBSTR",
    "SUBSTRING",
    "SUM",
    "TIME",
    "TRIM",
    "UPPER",
    "YEAR",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0).upper()
    if word in ("TRUE", "FALSE", "NULL"):
        return TokenType.KEYWORD_CONSTANT
    if word in ("CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE"):
        return TokenType.KEYWORD_DECLARATION
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word in _FUNCTIONS:
        return TokenType.NAME_FUNCTION
    return TokenType.NAME


class SqlLexer(PatternLexer):
    """SQL lexer. Thread-safe."""

    name = "sql"
    aliases = ("mysql", "postgresql", "sqlite")
    filenames = ("*.sql",)
    mimetypes = ("text/x-sql",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Comments
        Rule(re.compile(r"--.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        # Strings
        Rule(re.compile(r"'[^']*(?:''[^']*)*'"), TokenType.STRING_SINGLE),
        Rule(re.compile(r'"[^"]*(?:""[^"]*)*"'), TokenType.STRING_DOUBLE),
        # Backtick identifiers (MySQL)
        Rule(re.compile(r"`[^`]+`"), TokenType.NAME),
        # Numbers
        Rule(re.compile(r"\d+\.\d*(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\.\d+(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+"), TokenType.NUMBER_INTEGER),
        # Placeholders
        Rule(re.compile(r"\$\d+"), TokenType.NAME_VARIABLE),  # PostgreSQL
        Rule(re.compile(r"\?"), TokenType.NAME_VARIABLE),  # JDBC style
        Rule(re.compile(r":[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.NAME_VARIABLE),  # Named
        # Words (keywords, types, functions, identifiers)
        Rule(re.compile(_WORD_PATTERN, re.IGNORECASE), _classify_word),
        # Operators
        Rule(re.compile(r"<>|<=|>=|!=|::|->"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%<>=!|&]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{};,.]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
