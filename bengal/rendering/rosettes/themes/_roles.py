"""Semantic syntax roles for Rosettes theming.

Defines the semantic meaning of code elements, providing a layer
between token types and colors. Themes define colors for roles,
not individual tokens.

Thread-safe: StrEnum is immutable by design.
"""

from enum import StrEnum

__all__ = ["SyntaxRole"]


class SyntaxRole(StrEnum):
    """Semantic roles for syntax highlighting.

    Why a color, not just which color. Each role represents
    the purpose of a code element, enabling consistent theming
    across ~18 roles instead of 100+ token types.
    """

    # Control & Structure
    CONTROL_FLOW = "control"
    DECLARATION = "declaration"
    IMPORT = "import"

    # Data & Literals
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"

    # Identifiers
    TYPE = "type"
    FUNCTION = "function"
    VARIABLE = "variable"
    CONSTANT = "constant"

    # Documentation
    COMMENT = "comment"
    DOCSTRING = "docstring"

    # Feedback
    ERROR = "error"
    WARNING = "warning"
    ADDED = "added"
    REMOVED = "removed"

    # Base
    TEXT = "text"
    MUTED = "muted"

    # Additional roles
    PUNCTUATION = "punctuation"
    OPERATOR = "operator"
    ATTRIBUTE = "attribute"
    NAMESPACE = "namespace"
    TAG = "tag"
    REGEX = "regex"
    ESCAPE = "escape"
