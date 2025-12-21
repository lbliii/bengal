"""
Shared utilities for directive implementations.

Consolidates common helper functions to eliminate duplication across
directive files.

Architecture:
    These utilities are used by BengalDirective base class and can be
    imported directly by directives needing standalone access.

Related:
    - bengal/directives/base.py: Uses these utilities
"""

from __future__ import annotations

from typing import Any


def escape_html(text: str) -> str:
    """
    Escape HTML special characters for use in attributes.

    Escapes: & < > " '

    Args:
        text: Raw text to escape

    Returns:
        HTML-escaped text safe for use in attributes

    Example:
        >>> escape_html('Click "here" & win <prizes>')
        'Click &quot;here&quot; &amp; win &lt;prizes&gt;'
    """
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def build_class_string(*classes: str) -> str:
    """
    Build CSS class string from multiple class sources.

    Filters out empty strings and joins with space.

    Args:
        *classes: Variable number of class strings (may be empty)

    Returns:
        Space-joined class string

    Example:
        >>> build_class_string("dropdown", "", "my-class")
        'dropdown my-class'
        >>> build_class_string("", "")
        ''
    """
    return " ".join(c.strip() for c in classes if c and c.strip())


def bool_attr(name: str, value: bool) -> str:
    """
    Return HTML boolean attribute string.

    Args:
        name: Attribute name (e.g., "open", "disabled")
        value: Whether to include the attribute

    Returns:
        " name" if value is True, "" otherwise

    Example:
        >>> bool_attr("open", True)
        ' open'
        >>> bool_attr("open", False)
        ''
    """
    return f" {name}" if value else ""


def data_attrs(**attrs: Any) -> str:
    """
    Build data-* attribute string from keyword arguments.

    Converts underscore names to hyphenated (data_foo -> data-foo).
    Skips None and empty string values.

    Args:
        **attrs: Attribute name-value pairs

    Returns:
        Space-joined data attribute string

    Example:
        >>> data_attrs(columns="auto", gap="medium")
        'data-columns="auto" data-gap="medium"'
        >>> data_attrs(count=3, empty="", none_val=None)
        'data-count="3"'
    """
    parts = []
    for key, value in attrs.items():
        if value is not None and value != "":
            key_str = key.replace("_", "-")
            parts.append(f'data-{key_str}="{escape_html(str(value))}"')
    return " ".join(parts)


def attr_str(name: str, value: str | None) -> str:
    """
    Return HTML attribute string if value is truthy.

    Args:
        name: Attribute name
        value: Attribute value (may be None or empty)

    Returns:
        ' name="value"' if value is truthy, "" otherwise

    Example:
        >>> attr_str("href", "https://example.com")
        ' href="https://example.com"'
        >>> attr_str("href", None)
        ''
        >>> attr_str("href", "")
        ''
    """
    if value:
        return f' {name}="{escape_html(value)}"'
    return ""


def class_attr(base_class: str, *extra_classes: str) -> str:
    """
    Build class attribute string.

    Convenience wrapper combining build_class_string with attribute formatting.

    Args:
        base_class: Primary class (always included if non-empty)
        *extra_classes: Additional classes to add

    Returns:
        ' class="..."' string or "" if no classes

    Example:
        >>> class_attr("dropdown", "open", "")
        ' class="dropdown open"'
        >>> class_attr("", "")
        ''
    """
    classes = build_class_string(base_class, *extra_classes)
    if classes:
        return f' class="{classes}"'
    return ""
