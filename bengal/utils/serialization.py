"""
Robust serialization utilities for Bengal.

Provides utilities for converting complex Python objects (dataclasses, enums, paths)
into JSON-serializable formats, with special handling for module reloads in
development environments.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def to_jsonable(value: Any) -> Any:
    """
    Convert a value to a JSON-serializable form.
    
    Features:
    - Handles standard primitives (str, int, float, bool, None)
    - Recursively handles collections (dict, list, tuple, set)
    - Robust dataclass detection (handles reloaded modules via __dataclass_fields__)
    - Preserves tuples (useful for frozen dataclass reconstruction)
    - Converts Path objects to strings
    - Best-effort fallback to str() for unknown types
    
    Args:
        value: Object to convert
    
    Returns:
        JSON-serializable representation
        
    """
    if value is None:
        return None
    if isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Path):
        return str(value)

    # Handle dataclasses (including those from reloaded modules where is_dataclass might fail)
    if is_dataclass(value) or hasattr(value, "__dataclass_fields__"):
        try:
            # asdict() is recursive and handles most cases efficiently.
            # We call to_jsonable on the result to ensure any nested objects
            # asdict might have missed (e.g. non-dataclasses) are also handled.
            return to_jsonable(asdict(value)) if not isinstance(value, dict) else value
        except Exception:
            # Fallback for extreme cases (e.g. broken descriptors during reload)
            # Manual conversion via __dataclass_fields__
            fields = getattr(value, "__dataclass_fields__", {})
            return {
                name: to_jsonable(getattr(value, name))
                for name in fields
                if not name.startswith("_")
            }

    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list | set):
        return [to_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return tuple(to_jsonable(v) for v in value)

    # Last resort: represent unknown objects as strings (stable enough for caching)
    # but log a warning so we can track down what bypassed serialization
    if value is not None and not isinstance(value, str | int | float | bool):
        # Use a more descriptive fallback name for logger
        logger.debug(
            "serialization_fallback",
            extra={
                "type": type(value).__name__,
                "value_preview": str(value)[:100],
                "action": "converting_to_string",
            },
        )
    return str(value)
