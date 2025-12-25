"""Core types for Kida template engine.

This module defines the fundamental types used throughout Kida:
- Token: Lexer output unit
- TokenType: Token classification enum

All types are designed for immutability and thread-safety.
"""

from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    """Classification of lexer tokens.

    Categories:
        - Delimiters: Block, variable, comment markers
        - Literals: Strings, numbers, booleans
        - Identifiers: Names, keywords
        - Operators: Arithmetic, comparison, logical
        - Punctuation: Parentheses, brackets, dots
        - Special: EOF, whitespace, data (raw text)
    """

    # Delimiters
    BLOCK_BEGIN = "block_begin"  # {%
    BLOCK_END = "block_end"  # %}
    VARIABLE_BEGIN = "variable_begin"  # {{
    VARIABLE_END = "variable_end"  # }}
    COMMENT_BEGIN = "comment_begin"  # {#
    COMMENT_END = "comment_end"  # #}

    # Raw text between template constructs
    DATA = "data"

    # Literals
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"

    # Identifiers and keywords
    NAME = "name"

    # Operators
    ADD = "add"  # +
    SUB = "sub"  # -
    MUL = "mul"  # *
    DIV = "div"  # /
    FLOORDIV = "floordiv"  # //
    MOD = "mod"  # %
    POW = "pow"  # **

    # Comparison
    EQ = "eq"  # ==
    NE = "ne"  # !=
    LT = "lt"  # <
    LE = "le"  # <=
    GT = "gt"  # >
    GE = "ge"  # >=

    # Logical
    AND = "and"
    OR = "or"
    NOT = "not"

    # Membership & Identity
    IN = "in"
    NOT_IN = "not_in"
    IS = "is"
    IS_NOT = "is_not"

    # Assignment
    ASSIGN = "assign"  # =

    # Punctuation
    DOT = "dot"  # .
    COMMA = "comma"  # ,
    COLON = "colon"  # :
    PIPE = "pipe"  # |
    TILDE = "tilde"  # ~
    LPAREN = "lparen"  # (
    RPAREN = "rparen"  # )
    LBRACKET = "lbracket"  # [
    RBRACKET = "rbracket"  # ]
    LBRACE = "lbrace"  # {
    RBRACE = "rbrace"  # }

    # Special
    EOF = "eof"
    NEWLINE = "newline"
    WHITESPACE = "whitespace"


@dataclass(frozen=True, slots=True)
class Token:
    """A single token from the lexer.

    Attributes:
        type: Classification of this token
        value: The actual text/value of the token
        lineno: 1-based line number in source
        col_offset: 0-based column offset in source

    Immutable by design for thread-safety.

    Example:
        >>> token = Token(TokenType.NAME, "user", 1, 5)
        >>> token.type
        <TokenType.NAME: 'name'>
        >>> token.value
        'user'
    """

    type: TokenType
    value: str
    lineno: int
    col_offset: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.lineno}:{self.col_offset})"


# Keywords recognized by the parser
KEYWORDS = frozenset(
    {
        # Control flow
        "if",
        "elif",
        "else",
        "endif",
        "for",
        "endfor",
        "while",
        "endwhile",
        # Template structure
        "block",
        "endblock",
        "extends",
        "include",
        "import",
        "from",
        "macro",
        "endmacro",
        "call",
        "endcall",
        # Variables (Kida additions)
        "let",
        "set",
        "export",
        # Async (Kida native)
        "async",
        "await",
        # Logic
        "and",
        "or",
        "not",
        "in",
        "is",
        # Literals
        "true",
        "false",
        "none",
        # Filters/tests
        "with",
        "endwith",
        "filter",
        "endfilter",
        # Misc
        "raw",
        "endraw",
        "autoescape",
        "endautoescape",
        "do",  # Statement expression
        # Special
        "as",
        "recursive",
        "scoped",
        "required",
        "ignore",
        "missing",
    }
)


# Operator precedence (higher = binds tighter)
PRECEDENCE = {
    TokenType.OR: 1,
    TokenType.AND: 2,
    TokenType.NOT: 3,
    TokenType.IN: 4,
    TokenType.NOT_IN: 4,
    TokenType.IS: 4,
    TokenType.IS_NOT: 4,
    TokenType.EQ: 5,
    TokenType.NE: 5,
    TokenType.LT: 5,
    TokenType.LE: 5,
    TokenType.GT: 5,
    TokenType.GE: 5,
    TokenType.PIPE: 6,
    TokenType.TILDE: 7,
    TokenType.ADD: 8,
    TokenType.SUB: 8,
    TokenType.MUL: 9,
    TokenType.DIV: 9,
    TokenType.FLOORDIV: 9,
    TokenType.MOD: 9,
    TokenType.POW: 10,
}
