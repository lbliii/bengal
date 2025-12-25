"""Core types for Rosettes syntax highlighting.

Thread-safe, immutable types for tokenization.
"""

from enum import StrEnum
from typing import NamedTuple

__all__ = ["TokenType", "Token"]


class TokenType(StrEnum):
    """Semantic token types with Pygments-compatible CSS class names.

    Each value is the CSS class suffix used by Pygments themes.
    This ensures drop-in compatibility with existing Pygments stylesheets.
    """

    # Keywords
    KEYWORD = "k"
    KEYWORD_CONSTANT = "kc"
    KEYWORD_DECLARATION = "kd"
    KEYWORD_NAMESPACE = "kn"
    KEYWORD_PSEUDO = "kp"
    KEYWORD_RESERVED = "kr"
    KEYWORD_TYPE = "kt"

    # Names
    NAME = "n"
    NAME_ATTRIBUTE = "na"
    NAME_BUILTIN = "nb"
    NAME_BUILTIN_PSEUDO = "bp"
    NAME_CLASS = "nc"
    NAME_CONSTANT = "no"
    NAME_DECORATOR = "nd"
    NAME_ENTITY = "ni"
    NAME_EXCEPTION = "ne"
    NAME_FUNCTION = "nf"
    NAME_FUNCTION_MAGIC = "fm"
    NAME_LABEL = "nl"
    NAME_NAMESPACE = "nn"
    NAME_OTHER = "nx"
    NAME_PROPERTY = "py"
    NAME_TAG = "nt"
    NAME_VARIABLE = "nv"
    NAME_VARIABLE_CLASS = "vc"
    NAME_VARIABLE_GLOBAL = "vg"
    NAME_VARIABLE_INSTANCE = "vi"
    NAME_VARIABLE_MAGIC = "vm"

    # Literals
    LITERAL = "l"
    LITERAL_DATE = "ld"
    STRING = "s"
    STRING_AFFIX = "sa"
    STRING_BACKTICK = "sb"
    STRING_CHAR = "sc"
    STRING_DELIMITER = "dl"
    STRING_DOC = "sd"
    STRING_DOUBLE = "s2"
    STRING_ESCAPE = "se"
    STRING_HEREDOC = "sh"
    STRING_INTERPOL = "si"
    STRING_OTHER = "sx"
    STRING_REGEX = "sr"
    STRING_SINGLE = "s1"
    STRING_SYMBOL = "ss"
    NUMBER = "m"
    NUMBER_BIN = "mb"
    NUMBER_FLOAT = "mf"
    NUMBER_HEX = "mh"
    NUMBER_INTEGER = "mi"
    NUMBER_INTEGER_LONG = "il"
    NUMBER_OCT = "mo"

    # Operators
    OPERATOR = "o"
    OPERATOR_WORD = "ow"

    # Punctuation
    PUNCTUATION = "p"
    PUNCTUATION_MARKER = "pm"

    # Comments
    COMMENT = "c"
    COMMENT_HASHBANG = "ch"
    COMMENT_MULTILINE = "cm"
    COMMENT_PREPROC = "cp"
    COMMENT_PREPROCFILE = "cpf"
    COMMENT_SINGLE = "c1"
    COMMENT_SPECIAL = "cs"

    # Generic (for diffs, etc.)
    GENERIC = "g"
    GENERIC_DELETED = "gd"
    GENERIC_EMPH = "ge"
    GENERIC_ERROR = "gr"
    GENERIC_HEADING = "gh"
    GENERIC_INSERTED = "gi"
    GENERIC_OUTPUT = "go"
    GENERIC_PROMPT = "gp"
    GENERIC_STRONG = "gs"
    GENERIC_SUBHEADING = "gu"
    GENERIC_TRACEBACK = "gt"

    # Special
    TEXT = ""
    WHITESPACE = "w"
    ERROR = "err"
    OTHER = "x"


class Token(NamedTuple):
    """Immutable token — thread-safe, minimal memory.

    Attributes:
        type: The semantic type of the token.
        value: The actual text content of the token.
        line: 1-based line number where token starts.
        column: 1-based column number where token starts.
    """

    type: TokenType
    value: str
    line: int = 1
    column: int = 1
