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
- ``get_markdown_instance``: Get the Markdown parser instance from a renderer.

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


def get_markdown_instance(renderer: Any) -> Any | None:
    """
    Get the Markdown parser instance from a Mistune renderer.

    Mistune renderers may have the parser instance available as either
    ``_md`` (internal attribute) or ``md`` (public attribute) depending
    on the Mistune version and configuration. This helper abstracts the
    access pattern for consistent inline markdown parsing in directives.

    Consolidates pattern from:
        - bengal/directives/glossary.py (_parse_inline_markdown)
        - bengal/directives/steps.py (_parse_inline_markdown)

    Args:
        renderer: Mistune renderer instance

    Returns:
        The Markdown parser instance (with ``inline()`` method) or None
        if not available.

    Example:
            >>> md = get_markdown_instance(renderer)
            >>> if md and hasattr(md, 'inline'):
            ...     html = md.inline("**bold** text")

    """
    return getattr(renderer, "_md", None) or getattr(renderer, "md", None)


def escape_html(text: str) -> str:
    """Escape HTML special characters for safe use in attributes.

    Escapes the following characters:
        - ``&`` → ``&amp;``
        - ``<`` → ``&lt;``
        - ``>`` → ``&gt;``
        - ``"`` → ``&quot;``
        - ``'`` → ``&#x27;``

    This is a convenience re-export of the canonical implementation.

    Args:
        text: Raw text to escape.

    Returns:
        HTML-escaped string safe for use in attribute values.

    Example:
            >>> escape_html('Click "here" & win <prizes>')
            'Click &quot;here&quot; &amp; win &lt;prizes&gt;'
            >>> escape_html("")
            ''

    See Also:
        ``bengal.utils.text.escape_html``: Canonical implementation.

    """
    from bengal.utils.primitives.text import escape_html as _escape_html

    return _escape_html(text)


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


def ensure_badge_base_class(css_class: str) -> str:
    """
    Ensure badge CSS has a base class (badge or api-badge).

    Handles cases like "badge-secondary", "badge-danger", "api-badge", etc.
    If no base class is present, prepends the appropriate one based on
    existing modifier classes.

    Consolidates implementations from:
    - bengal/directives/badge.py (_ensure_base_class)
    - bengal/parsing/backends/patitas/directives/builtins/inline.py (_ensure_base_class)

    Args:
        css_class: Input CSS class string (may be empty or contain modifiers only).

    Returns:
        CSS class string with appropriate base class prepended if needed.

    Examples:
        >>> ensure_badge_base_class("")
        'badge badge-secondary'
        >>> ensure_badge_base_class("badge-primary")
        'badge badge-primary'
        >>> ensure_badge_base_class("badge badge-primary")
        'badge badge-primary'
        >>> ensure_badge_base_class("api-badge-warning")
        'api-badge api-badge-warning'
        >>> ensure_badge_base_class("custom-class")
        'badge custom-class'

    """
    if not css_class:
        return "badge badge-secondary"

    classes = css_class.split()

    # Check if base class is already present
    has_base_badge = any(cls in ("badge", "api-badge") for cls in classes)

    if not has_base_badge:
        # Determine which base class to use
        if any(cls.startswith("api-badge") for cls in classes):
            classes.insert(0, "api-badge")
        elif any(cls.startswith("badge-") for cls in classes):
            classes.insert(0, "badge")
        else:
            classes.insert(0, "badge")

        return " ".join(classes)

    return css_class


def clean_soundcloud_path(url_path: str) -> str:
    """
    Clean and normalize a SoundCloud URL path.

    Removes the domain prefix and query parameters to extract the
    username/track-name path.

    Consolidates implementations from:
    - bengal/directives/embed.py (_clean_path in SoundCloudEmbed)
    - bengal/parsing/backends/patitas/directives/builtins/embed.py (_clean_path)

    Args:
        url_path: SoundCloud URL or path (e.g., "https://soundcloud.com/user/track?si=xxx")

    Returns:
        Cleaned path (e.g., "user/track")

    Examples:
        >>> clean_soundcloud_path("https://soundcloud.com/artist/song")
        'artist/song'
        >>> clean_soundcloud_path("soundcloud.com/artist/song")
        'artist/song'
        >>> clean_soundcloud_path("artist/song?si=abc")
        'artist/song'
        >>> clean_soundcloud_path("artist/song")
        'artist/song'

    """
    cleaned = url_path
    if cleaned.startswith("https://soundcloud.com/"):
        cleaned = cleaned[23:]
    elif cleaned.startswith("soundcloud.com/"):
        cleaned = cleaned[15:]
    if "?" in cleaned:
        cleaned = cleaned.split("?")[0]
    return cleaned
