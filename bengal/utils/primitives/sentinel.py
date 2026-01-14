"""Sentinel values for unambiguous missing/undefined states.

Adopted from Jinja2's missing sentinel pattern to distinguish between
a value being None vs. a value being absent.
"""

from __future__ import annotations

from typing import Any


class _MissingType:
    """Sentinel for missing values (distinct from None)."""

    __slots__ = ()
    _instance: _MissingType | None = None

    def __new__(cls) -> _MissingType:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False

    def __reduce__(self) -> str:
        """Allow pickling the singleton."""
        return "MISSING"


MISSING: Any = _MissingType()
"""Sentinel value indicating a missing/unset value (distinct from None)."""


def is_missing(value: Any) -> bool:
    """Check if a value is the MISSING sentinel."""
    return value is MISSING
