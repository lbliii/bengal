"""Hand-written SQL lexer using composable scanner mixins.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._config import LexerConfig
from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._scanners import (
    DIGITS,
    scan_block_comment,
)
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer

__all__ = ["SqlStateMachineLexer"]


_KEYWORDS: frozenset[str] = frozenset(
    {
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
        # Common additions
        "OFFSET",
        "FETCH",
        "FIRST",
        "NEXT",
        "ROWS",
        "ONLY",
        "RETURNING",
        "CONFLICT",
        "DO",
        "NOTHING",
        "EXCLUDED",
        "USING",
        "CROSS",
        "NATURAL",
        "CASCADE",
        "RESTRICT",
        "TEMPORARY",
        "TEMP",
        "TRUNCATE",
        "COMMIT",
        "ROLLBACK",
        "BEGIN",
        "TRANSACTION",
        "SAVEPOINT",
        "GRANT",
        "REVOKE",
    }
)

_TYPES: frozenset[str] = frozenset(
    {
        "INT",
        "INTEGER",
        "SMALLINT",
        "BIGINT",
        "TINYINT",
        "DECIMAL",
        "NUMERIC",
        "FLOAT",
        "REAL",
        "DOUBLE",
        "PRECISION",
        "CHAR",
        "VARCHAR",
        "TEXT",
        "NCHAR",
        "NVARCHAR",
        "NTEXT",
        "BINARY",
        "VARBINARY",
        "IMAGE",
        "DATE",
        "TIME",
        "DATETIME",
        "DATETIME2",
        "TIMESTAMP",
        "BOOLEAN",
        "BOOL",
        "BIT",
        "MONEY",
        "UUID",
        "JSON",
        "JSONB",
        "XML",
        "ARRAY",
        "SERIAL",
        "BIGSERIAL",
    }
)

_FUNCTIONS: frozenset[str] = frozenset(
    {
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
        "COALESCE",
        "NULLIF",
        "CAST",
        "CONVERT",
        "CONCAT",
        "SUBSTRING",
        "TRIM",
        "LTRIM",
        "RTRIM",
        "UPPER",
        "LOWER",
        "LENGTH",
        "LEN",
        "REPLACE",
        "REVERSE",
        "LEFT",
        "RIGHT",
        "NOW",
        "CURRENT_DATE",
        "CURRENT_TIME",
        "CURRENT_TIMESTAMP",
        "GETDATE",
        "DATEADD",
        "DATEDIFF",
        "DATEPART",
        "YEAR",
        "MONTH",
        "DAY",
        "HOUR",
        "MINUTE",
        "SECOND",
        "ABS",
        "ROUND",
        "FLOOR",
        "CEILING",
        "CEIL",
        "POWER",
        "SQRT",
        "MOD",
        "RAND",
        "RANDOM",
        "ROW_NUMBER",
        "RANK",
        "DENSE_RANK",
        "NTILE",
        "LAG",
        "LEAD",
        "FIRST_VALUE",
        "LAST_VALUE",
    }
)


class SqlStateMachineLexer(StateMachineLexer):
    """SQL lexer with -- and /* */ comments."""

    name = "sql"
    aliases = ("mysql", "postgresql", "postgres")
    filenames = ("*.sql",)
    mimetypes = ("text/x-sql",)

    def tokenize(
        self,
        code: str,
        config: LexerConfig | None = None,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> Iterator[Token]:
        pos = start
        length = end if end is not None else len(code)
        line = 1
        line_start = start

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

            # Whitespace
            if char in self.WHITESPACE:
                start = pos
                start_line = line
                while pos < length and code[pos] in self.WHITESPACE:
                    if code[pos] == "\n":
                        line += 1
                        line_start = pos + 1
                    pos += 1
                yield Token(TokenType.WHITESPACE, code[start:pos], start_line, col)
                continue

            # Line comment --
            if char == "-" and pos + 1 < length and code[pos + 1] == "-":
                start = pos
                while pos < length and code[pos] != "\n":
                    pos += 1
                yield Token(TokenType.COMMENT_SINGLE, code[start:pos], line, col)
                continue

            # Block comment /* */
            if char == "/" and pos + 1 < length and code[pos + 1] == "*":
                start = pos
                pos = scan_block_comment(code, pos + 2, "*/")
                value = code[start:pos]
                newlines = value.count("\n")
                yield Token(TokenType.COMMENT_MULTILINE, value, line, col)
                if newlines:
                    line += newlines
                    line_start = start + value.rfind("\n") + 1
                continue

            # Strings (single quote)
            if char == "'":
                start = pos
                pos += 1
                while pos < length:
                    if code[pos] == "'":
                        if pos + 1 < length and code[pos + 1] == "'":
                            pos += 2  # Escaped quote
                            continue
                        pos += 1
                        break
                    pos += 1
                yield Token(TokenType.STRING, code[start:pos], line, col)
                continue

            # Identifiers (double quote or backtick)
            if char in '"`':
                start = pos
                quote = char
                pos += 1
                while pos < length and code[pos] != quote:
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.NAME, code[start:pos], line, col)
                continue

            # Bracketed identifiers [name]
            if char == "[":
                start = pos
                pos += 1
                while pos < length and code[pos] != "]":
                    pos += 1
                if pos < length:
                    pos += 1
                yield Token(TokenType.NAME, code[start:pos], line, col)
                continue

            # Numbers
            if char in DIGITS or (char == "." and pos + 1 < length and code[pos + 1] in DIGITS):
                start = pos
                if char == ".":
                    pos += 1
                while pos < length and code[pos] in DIGITS:
                    pos += 1
                if pos < length and code[pos] == ".":
                    pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                if pos < length and code[pos] in "eE":
                    pos += 1
                    if pos < length and code[pos] in "+-":
                        pos += 1
                    while pos < length and code[pos] in DIGITS:
                        pos += 1
                value = code[start:pos]
                token_type = (
                    TokenType.NUMBER_FLOAT
                    if "." in value or "e" in value.lower()
                    else TokenType.NUMBER_INTEGER
                )
                yield Token(token_type, value, line, col)
                continue

            # Keywords, types, and identifiers
            if char.isalpha() or char == "_":
                start = pos
                while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                    pos += 1
                word = code[start:pos]
                upper = word.upper()
                if upper in _KEYWORDS:
                    yield Token(TokenType.KEYWORD, word, line, col)
                elif upper in _TYPES:
                    yield Token(TokenType.KEYWORD_TYPE, word, line, col)
                elif upper in _FUNCTIONS:
                    yield Token(TokenType.NAME_BUILTIN, word, line, col)
                elif upper in ("TRUE", "FALSE", "NULL"):
                    yield Token(TokenType.KEYWORD_CONSTANT, word, line, col)
                else:
                    yield Token(TokenType.NAME, word, line, col)
                continue

            # Bind parameters :name or $1 or ?
            if char in ":$" or char == "?":
                start = pos
                pos += 1
                if char != "?" and pos < length:
                    if code[pos] in DIGITS:
                        while pos < length and code[pos] in DIGITS:
                            pos += 1
                    elif code[pos].isalpha() or code[pos] == "_":
                        while pos < length and (code[pos].isalnum() or code[pos] == "_"):
                            pos += 1
                yield Token(TokenType.NAME_VARIABLE, code[start:pos], line, col)
                continue

            # Operators
            if char in "=<>!":
                start = pos
                pos += 1
                if pos < length and code[pos] in "=<>":
                    pos += 1
                yield Token(TokenType.OPERATOR, code[start:pos], line, col)
                continue

            if char in "+-*/%|&^~":
                yield Token(TokenType.OPERATOR, char, line, col)
                pos += 1
                continue

            # Punctuation
            if char in "()[]{},.;":
                yield Token(TokenType.PUNCTUATION, char, line, col)
                pos += 1
                continue

            yield Token(TokenType.ERROR, char, line, col)
            pos += 1
