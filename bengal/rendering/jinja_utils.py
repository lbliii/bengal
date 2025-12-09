"""
Jinja2 utility functions for template development.

Provides helpers for working with Jinja2's Undefined objects and accessing
template context safely.
"""

from __future__ import annotations

from typing import Any

from jinja2 import is_undefined as jinja_is_undefined

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


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
    Undefined objects and returns default for missing attributes, even when
    __getattr__ is implemented.

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
        # Check if accessing attribute on primitive types - return default instead
        if isinstance(obj, str | int | float | bool | bytes):
            # Primitives shouldn't have custom attributes accessed in templates
            return default

        # Try to get the attribute
        value = getattr(obj, attr, default)

        # Check if value is Undefined
        if jinja_is_undefined(value):
            return default

        # Special case: if value is None, check if attribute actually exists
        # This handles objects with __getattr__ that return None for missing attrs
        if value is None:
            # Check if attribute exists in instance __dict__
            if hasattr(obj, "__dict__") and attr in obj.__dict__:
                return None  # Explicitly set to None
            # Check if it's a class attribute
            try:
                cls_value = getattr(type(obj), attr, _sentinel := object())
                if cls_value is not _sentinel:
                    return None  # Class attribute exists
            except (AttributeError, TypeError):
                pass
            # If we got None but attribute doesn't exist, return default
            # This likely came from __getattr__ returning None
            if default is not None:
                return default

        return value
    except (AttributeError, TypeError, ValueError, Exception) as e:
        # Catch all exceptions from property access
        # Properties can raise any exception, not just AttributeError
        logger.debug(
            "jinja_safe_getattr_failed",
            obj_type=type(obj).__name__,
            attr=attr,
            error=str(e),
            error_type=type(e).__name__,
            action="returning_default",
        )
        return default


def has_value(value: Any) -> bool:
    """
    Check if value is defined and not None/empty.

    More strict than is_undefined() - also checks for None and falsy values.
    Returns False for: Undefined, None, False, 0, "", [], {}

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
        >>> has_value(False)
        False
    """
    # Check if undefined first
    if jinja_is_undefined(value):
        return False
    # Then check if truthy (this handles None, 0, "", [], {}, False, etc.)
    return bool(value)


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
    Ensure value is defined and not None, replacing Undefined/None with default.

    This is useful in templates to ensure a value is always usable, even if
    it's missing or explicitly set to None.

    Args:
        value: Value to check
        default: Default value to use if undefined or None (default: "")

    Returns:
        Original value if defined and not None, default otherwise

    Example:
        >>> ensure_defined("hello")
        'hello'
        >>> ensure_defined(Undefined(), "fallback")
        'fallback'
        >>> ensure_defined(None, "fallback")
        'fallback'
        >>> ensure_defined(0)  # 0 is a valid value
        0
    """
    # Replace Undefined or None with default
    if jinja_is_undefined(value) or value is None:
        return default
    return value
