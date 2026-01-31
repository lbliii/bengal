"""
Type introspection utilities for runtime type analysis.

Provides functions for working with Python type hints at runtime, including
detection and unwrapping of Optional types, Union handling, and human-readable
type name formatting.

These utilities are used by:
- Schema validation (collections/validator.py)
- Directive option parsing (directives/options.py)
- Any code that needs runtime type introspection

Functions:
    is_optional_type: Check if a type hint allows None
    unwrap_optional: Extract the non-None type from Optional[X]
    type_display_name: Human-readable type name for error messages
    is_union_type: Check if a type is a Union (including X | Y syntax)
    get_union_args: Get all type arguments from a Union

Example:
    >>> from bengal.utils.primitives.types import is_optional_type, unwrap_optional
    >>> is_optional_type(str | None)
    True
    >>> unwrap_optional(str | None)
    <class 'str'>
    >>> is_optional_type(str)
    False

"""

from __future__ import annotations

import types
from typing import Any, Union, get_args, get_origin


def is_union_type(type_hint: Any) -> bool:
    """
    Check if a type hint is a Union type.

    Handles both ``typing.Union`` and Python 3.10+ ``X | Y`` syntax
    (``types.UnionType``).

    Args:
        type_hint: The type hint to check.

    Returns:
        True if the type is a Union (including ``X | Y``), False otherwise.

    Example:
        >>> is_union_type(str | int)
        True
        >>> is_union_type(Union[str, int])
        True
        >>> is_union_type(list[str])
        False

    """
    origin = get_origin(type_hint)
    return origin is Union or origin is types.UnionType


def get_union_args(type_hint: Any) -> tuple[Any, ...]:
    """
    Get the type arguments from a Union type.

    Works with both ``typing.Union`` and ``types.UnionType`` (``X | Y``).

    Args:
        type_hint: A Union type hint.

    Returns:
        Tuple of type arguments, or empty tuple if not a Union.

    Example:
        >>> get_union_args(str | int | None)
        (str, int, NoneType)
        >>> get_union_args(str)
        ()

    """
    if is_union_type(type_hint):
        return get_args(type_hint)
    return ()


def is_optional_type(type_hint: Any) -> bool:
    """
    Check if a type hint allows None values.

    Returns True for:
    - ``Optional[X]`` (which is ``Union[X, None]``)
    - ``X | None`` (Python 3.10+ union syntax)
    - ``Union[X, Y, None]`` (any Union containing NoneType)

    Args:
        type_hint: The type hint to check.

    Returns:
        True if the type allows None, False otherwise.

    Example:
        >>> is_optional_type(str | None)
        True
        >>> is_optional_type(Optional[int])
        True
        >>> is_optional_type(str)
        False
        >>> is_optional_type(Union[str, int, None])
        True

    """
    if is_union_type(type_hint):
        args = get_args(type_hint)
        return type(None) in args
    return False


def unwrap_optional(type_hint: Any) -> Any:
    """
    Extract the non-None type from an Optional type hint.

    For ``Optional[X]`` or ``X | None``, returns ``X``.
    For ``Union[A, B, None]``, returns ``Union[A, B]`` if multiple non-None
    types exist, or just ``A`` if only one non-None type.
    For non-Optional types, returns the type unchanged.

    Args:
        type_hint: The type hint to unwrap.

    Returns:
        The inner type(s) without NoneType, or the original type if not Optional.

    Example:
        >>> unwrap_optional(str | None)
        <class 'str'>
        >>> unwrap_optional(Optional[int])
        <class 'int'>
        >>> unwrap_optional(str)
        <class 'str'>
        >>> unwrap_optional(Union[str, int, None])
        Union[str, int]

    """
    if not is_union_type(type_hint):
        return type_hint

    args = get_args(type_hint)
    non_none_args = tuple(a for a in args if a is not type(None))

    if len(non_none_args) == 0:
        # Union[None] edge case - just return None type
        return type(None)
    elif len(non_none_args) == 1:
        # Optional[X] -> X
        return non_none_args[0]
    else:
        # Union[A, B, None] -> Union[A, B]
        # Reconstruct the Union without None
        return Union[non_none_args]  # type: ignore[return-value]


def type_display_name(type_hint: Any) -> str:
    """
    Get a human-readable name for a type hint.

    Produces clean, readable type names suitable for error messages and
    documentation. Handles generics, Unions, Optional, and nested types.

    Args:
        type_hint: The type hint to format.

    Returns:
        A human-readable string representation of the type.

    Example:
        >>> type_display_name(str)
        'str'
        >>> type_display_name(list[str])
        'list[str]'
        >>> type_display_name(str | None)
        'Optional[str]'
        >>> type_display_name(str | int)
        'str | int'
        >>> type_display_name(dict[str, int])
        'dict[str, int]'

    """
    origin = get_origin(type_hint)

    # Handle Union types (including X | Y syntax)
    if is_union_type(type_hint):
        args = get_args(type_hint)

        # Check for Optional[X] pattern (Union with exactly one non-None type)
        if type(None) in args:
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                return f"Optional[{type_display_name(non_none[0])}]"

        # Multiple types in Union - use pipe syntax
        return " | ".join(type_display_name(a) for a in args)

    # Handle list[X]
    if origin is list:
        args = get_args(type_hint)
        if args:
            return f"list[{type_display_name(args[0])}]"
        return "list"

    # Handle dict[K, V]
    if origin is dict:
        args = get_args(type_hint)
        if args and len(args) >= 2:
            return f"dict[{type_display_name(args[0])}, {type_display_name(args[1])}]"
        return "dict"

    # Handle tuple[X, Y, ...]
    if origin is tuple:
        args = get_args(type_hint)
        if args:
            return f"tuple[{', '.join(type_display_name(a) for a in args)}]"
        return "tuple"

    # Handle set[X]
    if origin is set:
        args = get_args(type_hint)
        if args:
            return f"set[{type_display_name(args[0])}]"
        return "set"

    # Handle frozenset[X]
    if origin is frozenset:
        args = get_args(type_hint)
        if args:
            return f"frozenset[{type_display_name(args[0])}]"
        return "frozenset"

    # Handle NoneType
    if type_hint is type(None):
        return "None"

    # Handle regular types with __name__
    if hasattr(type_hint, "__name__"):
        return type_hint.__name__

    # Fallback to string representation
    return str(type_hint)


__all__ = [
    "get_union_args",
    "is_optional_type",
    "is_union_type",
    "type_display_name",
    "unwrap_optional",
]
