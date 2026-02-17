"""
Safe attribute and dictionary access utilities.

Provides unified safe access patterns for template rendering, handling
Jinja2 Undefined objects, missing attributes, and None values gracefully.

This module consolidates implementations from:
- bengal/rendering/jinja_utils.py (safe_get, safe_get_attr)
- bengal/rendering/template_functions/strings.py (dict_get)

Usage:
    from bengal.rendering.utils.safe_access import safe_get, safe_get_nested

    # Single attribute
    title = safe_get(page, "title", "Untitled")

    # Nested attributes
    name = safe_get_nested(user, "profile", "name", default="Unknown")

    # Dict or object access
    value = safe_get(obj, "key", "default")  # Works for both dicts and objects
"""

from __future__ import annotations

from typing import Any

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

# Sentinel for detecting missing values vs explicit None
_MISSING = object()


def is_undefined(value: Any) -> bool:
    """
    Check if a value is a Jinja2 Undefined object.

    This is a wrapper around jinja2.is_undefined() that provides a clean API
    for template function developers and avoids import overhead when not needed.

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
    try:
        from jinja2 import is_undefined as jinja_is_undefined

        return jinja_is_undefined(value)
    except ImportError:
        return False


def safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """
    Safely get attribute or key from object, handling Undefined and missing values.

    Works with both dict-like objects and regular objects with attributes.
    Returns default for: Jinja2 Undefined, None values, missing keys/attrs.

    Args:
        obj: Object to get value from (dict, object, or Jinja2 context)
        key: Attribute name or dict key
        default: Default value if undefined or missing (default: None)

    Returns:
        Value if found and defined, default otherwise

    Examples:
        # Object attribute access
        >>> safe_get(page, "title", "Untitled")
        'My Page'

        # Dict access
        >>> safe_get({"name": "test"}, "name", "default")
        'test'

        # Missing attribute returns default
        >>> safe_get(page, "nonexistent", "fallback")
        'fallback'

        # Jinja2 Undefined returns default
        >>> safe_get(Undefined(), "anything", "default")
        'default'

    Note:
        For primitives (str, int, float, bool, bytes), returns default
        as these shouldn't have custom attributes accessed in templates.

    """
    # Check if obj itself is undefined
    if is_undefined(obj):
        return default

    # Primitives shouldn't have custom attributes accessed in templates
    if isinstance(obj, str | int | float | bool | bytes):
        return default

    try:
        # Try dict access first (more common in templates)
        if isinstance(obj, dict):
            value = obj.get(key, _MISSING)
            if value is _MISSING:
                return default
            if is_undefined(value):
                return default
            return value if value is not None else default

        # Attribute access for objects
        value = getattr(obj, key, _MISSING)

        if value is _MISSING:
            return default

        if is_undefined(value):
            return default

        # Handle explicit None - check if attribute actually exists
        if value is None:
            # For explicit None attributes, return None (not default)
            # unless default is also not None
            if _attr_exists(obj, key):
                return None
            return default

        return value

    except (AttributeError, TypeError, ValueError, Exception) as e:
        logger.debug(
            "safe_get_failed",
            obj_type=type(obj).__name__,
            key=key,
            error=str(e),
            error_type=type(e).__name__,
            action="returning_default",
        )
        return default


def _attr_exists(obj: Any, attr: str) -> bool:
    """Check if attribute actually exists on object (vs __getattr__ returning None)."""
    # Check instance __dict__
    if hasattr(obj, "__dict__") and attr in obj.__dict__:
        return True

    # Check class attribute
    try:
        if hasattr(type(obj), attr):
            return True
    except AttributeError, TypeError:
        pass

    return False


def safe_get_nested(obj: Any, *attrs: str, default: Any = None) -> Any:
    """
    Safely get nested attribute from object using dot notation.

    Traverses a chain of attributes, returning default if any step
    fails or returns Undefined/None.

    Args:
        obj: Object to start traversal from
        *attrs: Attribute names to traverse
        default: Default value if any attribute is undefined/missing

    Returns:
        Final attribute value or default

    Examples:
        # Nested object access
        >>> safe_get_nested(user, "profile", "name", default="Unknown")
        'John'

        # Missing intermediate attribute
        >>> safe_get_nested(user, "profile", "missing", default="Unknown")
        'Unknown'

        # Dict with nested dicts
        >>> safe_get_nested(data, "config", "theme", "color", default="blue")
        'red'

    Note:
        Each step uses safe_get, so Undefined values are handled at every level.

    """
    if not attrs:
        return obj if not is_undefined(obj) else default

    current = obj

    for attr in attrs:
        if is_undefined(current) or current is None:
            return default

        try:
            # Use dict access for dicts, attribute access otherwise
            if isinstance(current, dict):
                current = current.get(attr)
            else:
                current = getattr(current, attr, None)

            if is_undefined(current):
                return default

        except AttributeError, TypeError:
            return default

    return current if current is not None else default


def has_value(value: Any) -> bool:
    """
    Check if value is defined and truthy.

    More strict than is_undefined() - also checks for None and falsy values.
    Returns False for: Undefined, None, False, 0, "", [], {}

    Args:
        value: Value to check

    Returns:
        True if value is defined and truthy

    Examples:
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
    if is_undefined(value):
        return False
    return bool(value)


def ensure_defined(value: Any, default: Any = "") -> Any:
    """
    Ensure value is defined and not None, replacing Undefined/None with default.

    Useful in templates to ensure a value is always usable.

    Args:
        value: Value to check
        default: Default value to use if undefined or None (default: "")

    Returns:
        Original value if defined and not None, default otherwise

    Examples:
        >>> ensure_defined("hello")
        'hello'
        >>> ensure_defined(Undefined(), "fallback")
        'fallback'
        >>> ensure_defined(None, "fallback")
        'fallback'
        >>> ensure_defined(0)  # 0 is a valid value
        0

    """
    if is_undefined(value) or value is None:
        return default
    return value
