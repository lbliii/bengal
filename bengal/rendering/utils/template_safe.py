"""
Decorator for template functions that may receive invalid types from YAML/config.

Catches common template errors (TypeError, ValueError, AttributeError, KeyError)
and returns a default instead of raising.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any


def template_safe[T](
    default: T | None = None,
    exceptions: tuple[type[BaseException], ...] = (
        TypeError,
        ValueError,
        AttributeError,
        KeyError,
    ),
) -> Callable[[Callable[..., T]], Callable[..., T | None]]:
    """Decorator that catches common template errors and returns default.

    Args:
        default: Value to return when an exception is caught.
        exceptions: Exception types to catch (default: TypeError, ValueError,
            AttributeError, KeyError).

    Returns:
        Decorated function that returns default on caught exceptions.

    Example:
        >>> @template_safe(default=0)
        ... def safe_div(a: int, b: int) -> float:
        ...     return a / b
        >>> safe_div(10, 2)
        5.0
        >>> safe_div(10, "x")
        0
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T | None]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T | None:
            try:
                return fn(*args, **kwargs)
            except exceptions:
                return default

        return wrapper

    return decorator
