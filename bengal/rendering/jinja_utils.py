"""
Jinja2 utility functions for template development.

Provides helpers for working with Jinja2's Undefined objects and accessing
template context safely.

This module re-exports consolidated utilities from bengal.rendering.utils.safe_access
for backward compatibility.
"""

from __future__ import annotations

# Re-export from consolidated module for backward compatibility
from bengal.rendering.utils.safe_access import (
    ensure_defined,
    has_value,
    is_undefined,
    safe_get,
    safe_get_nested as safe_get_attr,
)

__all__ = [
    "ensure_defined",
    "has_value",
    "is_undefined",
    "safe_get",
    "safe_get_attr",
]
