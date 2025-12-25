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

    Roles are grouped by category:
        - Control & Structure: Flow control, declarations, imports
        - Data & Literals: Strings, numbers, booleans
        - Identifiers: Types, functions, variables, constants
        - Documentation: Comments, docstrings
        - Feedback: Errors, warnings, diff additions/removals
        - Base: Default text, muted elements
    """

    # Control & Structure
    CONTROL_FLOW = "control"
    """Keywords that control execution: if, for, while, return, break, continue."""

    DECLARATION = "declaration"
    """Declaration keywords: def, class, let, const, fn, struct."""

    IMPORT = "import"
    """Import statements: import, from, require, use, include."""

    # Data & Literals
    STRING = "string"
    """String literals: "hello", 'world', `template`."""

    NUMBER = "number"
    """Numeric literals: 42, 3.14, 0xFF, 1e10."""

    BOOLEAN = "boolean"
    """Boolean literals: true, false, True, False, nil, null."""

    # Identifiers
    TYPE = "type"
    """Type names and annotations: class names, type hints."""

    FUNCTION = "function"
    """Function and method names (definitions and calls)."""

    VARIABLE = "variable"
    """Variable names (optional styling, often same as text)."""

    CONSTANT = "constant"
    """Constants: ALL_CAPS names, enum values."""

    # Documentation
    COMMENT = "comment"
    """Single and multi-line comments: # comment, // comment, /* */."""

    DOCSTRING = "docstring"
    """Documentation strings: '''docstring''', /** JSDoc */."""

    # Feedback
    ERROR = "error"
    """Syntax errors and invalid code."""

    WARNING = "warning"
    """Deprecation warnings, lint warnings."""

    ADDED = "added"
    """Diff: added/inserted lines (green in most themes)."""

    REMOVED = "removed"
    """Diff: removed/deleted lines (red in most themes)."""

    # Base
    TEXT = "text"
    """Default text, punctuation, operators when not specially styled."""

    MUTED = "muted"
    """De-emphasized elements: less important punctuation, whitespace indicators."""

    # Additional roles for fine-grained control
    PUNCTUATION = "punctuation"
    """Punctuation: brackets, braces, commas, semicolons."""

    OPERATOR = "operator"
    """Operators: +, -, *, /, ==, !=, etc."""

    ATTRIBUTE = "attribute"
    """Attributes and decorators: @decorator, HTML attributes."""

    NAMESPACE = "namespace"
    """Namespace and module names: package.module."""

    TAG = "tag"
    """Markup tags: HTML/XML tag names."""

    REGEX = "regex"
    """Regular expression literals."""

    ESCAPE = "escape"
    """Escape sequences in strings: \\n, \\t, \\x00."""
