"""Shared utilities for directive HTML generation.

This module provides helper functions for common HTML manipulation tasks
used across directive implementations, eliminating duplication and ensuring
consistent escaping and attribute formatting.

Functions:
    - ``escape_html``: Escape HTML special characters for safe attribute use.
    - ``build_class_string``: Combine multiple CSS classes into a single string.
    - ``bool_attr``: Generate HTML boolean attributes (e.g., ``open``, ``disabled``).
    - ``data_attrs``: Generate ``data-*`` attribute strings from keyword arguments.
    - ``attr_str``: Generate a single HTML attribute string.
    - ``class_attr``: Generate a ``class="..."`` attribute string.

Example:
    Building an HTML tag with utilities::

        from bengal.directives.utils import escape_html, class_attr, bool_attr

        title = escape_html(user_input)
        attrs = class_attr("dropdown", custom_class) + bool_attr("open", is_open)
        html = f'<details{attrs}><summary>{title}</summary>{content}</details>'

See Also:
    - ``bengal.directives.base``: ``BengalDirective`` exposes these as static methods.
"""

from __future__ import annotations

from typing import Any


def escape_html(text: str) -> str:
    """Escape HTML special characters for safe use in attributes.

    Escapes the following characters:
        - ``&`` → ``&amp;``
        - ``<`` → ``&lt;``
        - ``>`` → ``&gt;``
        - ``"`` → ``&quot;``
        - ``'`` → ``&#x27;``

    Args:
        text: Raw text to escape.

    Returns:
        HTML-escaped string safe for use in attribute values.

    Example:
        >>> escape_html('Click "here" & win <prizes>')
        'Click &quot;here&quot; &amp; win &lt;prizes&gt;'
        >>> escape_html("")
        ''
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
    """Build a CSS class string from multiple class sources.

    Filters out empty strings, strips whitespace, and joins with spaces.
    Useful when combining base classes with optional user-provided classes.

    Args:
        *classes: Variable number of class strings (may include empty strings).

    Returns:
        Space-joined class string, or empty string if no valid classes.

    Example:
        >>> build_class_string("dropdown", "", "my-class")
        'dropdown my-class'
        >>> build_class_string("", "")
        ''
        >>> build_class_string("base", "  extra  ", "")
        'base extra'
    """
    return " ".join(c.strip() for c in classes if c and c.strip())


def bool_attr(name: str, value: bool) -> str:
    """Generate an HTML boolean attribute string.

    Boolean attributes in HTML are present or absent, not ``="true"``/``="false"``.
    This function returns the attribute with a leading space when true.

    Args:
        name: Attribute name (e.g., ``"open"``, ``"disabled"``, ``"checked"``).
        value: Whether to include the attribute.

    Returns:
        ``" name"`` (with leading space) if value is ``True``, empty string otherwise.

    Example:
        >>> bool_attr("open", True)
        ' open'
        >>> bool_attr("open", False)
        ''
        >>> f'<details{bool_attr("open", is_open)}>'
        '<details open>'  # when is_open=True
    """
    return f" {name}" if value else ""


def data_attrs(**attrs: Any) -> str:
    """Build ``data-*`` attribute string from keyword arguments.

    Converts underscores in names to hyphens (``columns`` → ``data-columns``).
    Skips ``None`` and empty string values. Values are HTML-escaped.

    Args:
        **attrs: Attribute name-value pairs. Names are prefixed with ``data-``.

    Returns:
        Space-joined data attribute string, or empty string if no valid attrs.

    Example:
        >>> data_attrs(columns="auto", gap="medium")
        'data-columns="auto" data-gap="medium"'
        >>> data_attrs(count=3, empty="", none_val=None)
        'data-count="3"'
        >>> data_attrs()
        ''
    """
    parts = []
    for key, value in attrs.items():
        if value is not None and value != "":
            key_str = key.replace("_", "-")
            parts.append(f'data-{key_str}="{escape_html(str(value))}"')
    return " ".join(parts)


def attr_str(name: str, value: str | None) -> str:
    """Generate an HTML attribute string if value is truthy.

    Returns a formatted attribute with leading space when value is non-empty.
    The value is HTML-escaped for safe inclusion in attributes.

    Args:
        name: Attribute name (e.g., ``"href"``, ``"src"``, ``"title"``).
        value: Attribute value (may be ``None`` or empty string).

    Returns:
        ``' name="value"'`` (with leading space) if value is truthy, else ``""``.

    Example:
        >>> attr_str("href", "https://example.com")
        ' href="https://example.com"'
        >>> attr_str("href", None)
        ''
        >>> attr_str("title", 'Say "Hello"')
        ' title="Say &quot;Hello&quot;"'
    """
    if value:
        return f' {name}="{escape_html(value)}"'
    return ""


def class_attr(base_class: str, *extra_classes: str) -> str:
    """Build a ``class="..."`` attribute string.

    Convenience wrapper combining ``build_class_string()`` with attribute
    formatting. Returns empty string if no classes are provided.

    Args:
        base_class: Primary CSS class (included if non-empty).
        *extra_classes: Additional CSS classes to append.

    Returns:
        ``' class="..."'`` (with leading space) if any classes, else ``""``.

    Example:
        >>> class_attr("dropdown", "open", "")
        ' class="dropdown open"'
        >>> class_attr("", "")
        ''
        >>> f'<div{class_attr("card", user_class)}>'
        '<div class="card custom">'  # when user_class="custom"
    """
    classes = build_class_string(base_class, *extra_classes)
    if classes:
        return f' class="{classes}"'
    return ""
