"""Token type to semantic role mapping.

Maps Pygments-compatible TokenType values to semantic SyntaxRole values.
This provides the abstraction layer between tokens and colors.

Thread-safe: All data is immutable (dict lookups are atomic in CPython).
"""

from rosettes._types import TokenType
from rosettes.themes._roles import SyntaxRole

__all__ = ["ROLE_MAPPING", "PYGMENTS_CLASS_MAP", "get_role"]


# TokenType → SyntaxRole mapping
# Maps specific token types to their semantic roles
ROLE_MAPPING: dict[TokenType, SyntaxRole] = {
    # Keywords → Control/Declaration
    TokenType.KEYWORD: SyntaxRole.CONTROL_FLOW,
    TokenType.KEYWORD_CONSTANT: SyntaxRole.BOOLEAN,
    TokenType.KEYWORD_DECLARATION: SyntaxRole.DECLARATION,
    TokenType.KEYWORD_NAMESPACE: SyntaxRole.IMPORT,
    TokenType.KEYWORD_PSEUDO: SyntaxRole.CONTROL_FLOW,
    TokenType.KEYWORD_RESERVED: SyntaxRole.CONTROL_FLOW,
    TokenType.KEYWORD_TYPE: SyntaxRole.TYPE,
    # Names → Identity
    TokenType.NAME: SyntaxRole.VARIABLE,
    TokenType.NAME_ATTRIBUTE: SyntaxRole.ATTRIBUTE,
    TokenType.NAME_BUILTIN: SyntaxRole.FUNCTION,
    TokenType.NAME_BUILTIN_PSEUDO: SyntaxRole.CONSTANT,
    TokenType.NAME_CLASS: SyntaxRole.TYPE,
    TokenType.NAME_CONSTANT: SyntaxRole.CONSTANT,
    TokenType.NAME_DECORATOR: SyntaxRole.ATTRIBUTE,
    TokenType.NAME_ENTITY: SyntaxRole.CONSTANT,
    TokenType.NAME_EXCEPTION: SyntaxRole.TYPE,
    TokenType.NAME_FUNCTION: SyntaxRole.FUNCTION,
    TokenType.NAME_FUNCTION_MAGIC: SyntaxRole.FUNCTION,
    TokenType.NAME_LABEL: SyntaxRole.VARIABLE,
    TokenType.NAME_NAMESPACE: SyntaxRole.NAMESPACE,
    TokenType.NAME_OTHER: SyntaxRole.VARIABLE,
    TokenType.NAME_PROPERTY: SyntaxRole.ATTRIBUTE,
    TokenType.NAME_TAG: SyntaxRole.TAG,
    TokenType.NAME_VARIABLE: SyntaxRole.VARIABLE,
    TokenType.NAME_VARIABLE_CLASS: SyntaxRole.VARIABLE,
    TokenType.NAME_VARIABLE_GLOBAL: SyntaxRole.VARIABLE,
    TokenType.NAME_VARIABLE_INSTANCE: SyntaxRole.VARIABLE,
    TokenType.NAME_VARIABLE_MAGIC: SyntaxRole.CONSTANT,
    # Literals → Data
    TokenType.LITERAL: SyntaxRole.STRING,
    TokenType.LITERAL_DATE: SyntaxRole.NUMBER,
    TokenType.STRING: SyntaxRole.STRING,
    TokenType.STRING_AFFIX: SyntaxRole.STRING,
    TokenType.STRING_BACKTICK: SyntaxRole.STRING,
    TokenType.STRING_CHAR: SyntaxRole.STRING,
    TokenType.STRING_DELIMITER: SyntaxRole.STRING,
    TokenType.STRING_DOC: SyntaxRole.DOCSTRING,
    TokenType.STRING_DOUBLE: SyntaxRole.STRING,
    TokenType.STRING_ESCAPE: SyntaxRole.ESCAPE,
    TokenType.STRING_HEREDOC: SyntaxRole.STRING,
    TokenType.STRING_INTERPOL: SyntaxRole.ESCAPE,
    TokenType.STRING_OTHER: SyntaxRole.STRING,
    TokenType.STRING_REGEX: SyntaxRole.REGEX,
    TokenType.STRING_SINGLE: SyntaxRole.STRING,
    TokenType.STRING_SYMBOL: SyntaxRole.CONSTANT,
    # Numbers
    TokenType.NUMBER: SyntaxRole.NUMBER,
    TokenType.NUMBER_BIN: SyntaxRole.NUMBER,
    TokenType.NUMBER_FLOAT: SyntaxRole.NUMBER,
    TokenType.NUMBER_HEX: SyntaxRole.NUMBER,
    TokenType.NUMBER_INTEGER: SyntaxRole.NUMBER,
    TokenType.NUMBER_INTEGER_LONG: SyntaxRole.NUMBER,
    TokenType.NUMBER_OCT: SyntaxRole.NUMBER,
    # Operators
    TokenType.OPERATOR: SyntaxRole.OPERATOR,
    TokenType.OPERATOR_WORD: SyntaxRole.CONTROL_FLOW,
    # Punctuation
    TokenType.PUNCTUATION: SyntaxRole.PUNCTUATION,
    TokenType.PUNCTUATION_MARKER: SyntaxRole.PUNCTUATION,
    # Comments → Documentation
    TokenType.COMMENT: SyntaxRole.COMMENT,
    TokenType.COMMENT_HASHBANG: SyntaxRole.COMMENT,
    TokenType.COMMENT_MULTILINE: SyntaxRole.COMMENT,
    TokenType.COMMENT_PREPROC: SyntaxRole.ATTRIBUTE,
    TokenType.COMMENT_PREPROCFILE: SyntaxRole.STRING,
    TokenType.COMMENT_SINGLE: SyntaxRole.COMMENT,
    TokenType.COMMENT_SPECIAL: SyntaxRole.DOCSTRING,
    # Generic → Feedback
    TokenType.GENERIC: SyntaxRole.TEXT,
    TokenType.GENERIC_DELETED: SyntaxRole.REMOVED,
    TokenType.GENERIC_EMPH: SyntaxRole.TEXT,
    TokenType.GENERIC_ERROR: SyntaxRole.ERROR,
    TokenType.GENERIC_HEADING: SyntaxRole.DECLARATION,
    TokenType.GENERIC_INSERTED: SyntaxRole.ADDED,
    TokenType.GENERIC_OUTPUT: SyntaxRole.MUTED,
    TokenType.GENERIC_PROMPT: SyntaxRole.MUTED,
    TokenType.GENERIC_STRONG: SyntaxRole.TEXT,
    TokenType.GENERIC_SUBHEADING: SyntaxRole.DECLARATION,
    TokenType.GENERIC_TRACEBACK: SyntaxRole.ERROR,
    # Special
    TokenType.TEXT: SyntaxRole.TEXT,
    TokenType.WHITESPACE: SyntaxRole.TEXT,
    TokenType.ERROR: SyntaxRole.ERROR,
    TokenType.OTHER: SyntaxRole.MUTED,
}


# SyntaxRole → Pygments CSS class mapping
# Used when css_class_style="pygments" for backward compatibility
PYGMENTS_CLASS_MAP: dict[SyntaxRole, str] = {
    SyntaxRole.CONTROL_FLOW: "k",
    SyntaxRole.DECLARATION: "kd",
    SyntaxRole.IMPORT: "kn",
    SyntaxRole.STRING: "s",
    SyntaxRole.DOCSTRING: "sd",
    SyntaxRole.NUMBER: "m",
    SyntaxRole.BOOLEAN: "kc",
    SyntaxRole.TYPE: "nc",
    SyntaxRole.FUNCTION: "nf",
    SyntaxRole.VARIABLE: "nv",
    SyntaxRole.CONSTANT: "no",
    SyntaxRole.COMMENT: "c",
    SyntaxRole.ERROR: "err",
    SyntaxRole.WARNING: "w",
    SyntaxRole.ADDED: "gi",
    SyntaxRole.REMOVED: "gd",
    SyntaxRole.TEXT: "",
    SyntaxRole.MUTED: "x",
    SyntaxRole.PUNCTUATION: "p",
    SyntaxRole.OPERATOR: "o",
    SyntaxRole.ATTRIBUTE: "nd",
    SyntaxRole.NAMESPACE: "nn",
    SyntaxRole.TAG: "nt",
    SyntaxRole.REGEX: "sr",
    SyntaxRole.ESCAPE: "se",
}


def get_role(token_type: TokenType) -> SyntaxRole:
    """Get the semantic role for a token type.

    Args:
        token_type: The token type to map.

    Returns:
        The corresponding semantic role, or TEXT if not mapped.
    """
    return ROLE_MAPPING.get(token_type, SyntaxRole.TEXT)
