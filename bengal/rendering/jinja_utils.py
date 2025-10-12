"""
Jinja2 utility functions for template development.

Provides helpers for working with Jinja2's Undefined objects and accessing
template context safely.
"""

from typing import Any

from jinja2 import is_undefined as jinja_is_undefined


def is_undefined(value: Any) -> bool:
    """
    Check if a value is a Jinja2 Undefined object.

    This is a wrapper around jinja2.is_undefined() that provides a clean API
    for template function developers.

    Args:
        value: Value to check

    Returns:
        True if value is Undefined, False otherwise

    Example:
        >>> from jinja2 import Undefined
        >>> is_undefined(Undefined())
        True
        >>> is_undefined("hello")
        False
        >>> is_undefined(None)
        False
    """
    return jinja_is_undefined(value)


def safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    """
    Safely get attribute from object, handling Jinja2 Undefined values.

    This is a replacement for hasattr()/getattr() that also handles Jinja2's
    Undefined objects properly.

    Args:
        obj: Object to get attribute from
        attr: Attribute name
        default: Default value if undefined or missing

    Returns:
        Attribute value or default

    Example:
        >>> class Page:
        ...     title = "Hello"
        >>> safe_get(Page(), "title", "Untitled")
        'Hello'
        >>> safe_get(Page(), "missing", "Default")
        'Default'

        # In templates with Undefined objects:
        {% set title = safe_get(page, "title", "Untitled") %}
    """
    try:
        value = getattr(obj, attr, default)
        if jinja_is_undefined(value):
            return default
        return value
    except (AttributeError, TypeError):
        return default


def has_value(value: Any) -> bool:
    """
    Check if value is defined and not None/empty.

    More strict than is_undefined() - also checks for None and empty strings.

    Args:
        value: Value to check

    Returns:
        True if value is defined and truthy

    Example:
        >>> has_value("hello")
        True
        >>> has_value("")
        False
        >>> has_value(None)
        False
        >>> has_value(0)
        False
        >>> has_value([])
        False
    """
    return not jinja_is_undefined(value) and value is not None and value != ""


def safe_get_attr(obj: Any, *attrs: str, default: Any = None) -> Any:
    """
    Safely get nested attribute from object using dot notation.

    Args:
        obj: Object to get attribute from
        *attrs: Attribute names (can be nested)
        default: Default value if any attribute is undefined/missing

    Returns:
        Final attribute value or default

    Example:
        >>> class User:
        ...     class Profile:
        ...         name = "John"
        ...     profile = Profile()
        >>> safe_get_attr(user, "profile", "name", default="Unknown")
        'John'
        >>> safe_get_attr(user, "profile", "missing", default="Unknown")
        'Unknown'
    """
    current = obj

    for attr in attrs:
        try:
            current = getattr(current, attr, None)
            if current is None or jinja_is_undefined(current):
                return default
        except (AttributeError, TypeError):
            return default

    return current


def ensure_defined(value: Any, default: Any = "") -> Any:
    """
    Ensure value is defined, replacing Undefined with default.

    Args:
        value: Value to check
        default: Default value to use if undefined (default: "")

    Returns:
        Original value if defined, default otherwise

    Example:
        >>> ensure_defined("hello")
        'hello'
        >>> ensure_defined(Undefined(), "fallback")
        'fallback'
    """
    return default if jinja_is_undefined(value) else value
