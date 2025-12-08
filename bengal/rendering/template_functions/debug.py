"""
Debug utility functions for templates.

Provides 3 functions for debugging templates during development.
"""

from __future__ import annotations

import pprint
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.site import Site

logger = get_logger(__name__)


def register(env: Environment, site: Site) -> None:
    """Register debug utility functions with Jinja2 environment."""
    env.filters.update(
        {
            "debug": debug,
            "typeof": typeof,
            "inspect": inspect,
        }
    )


def debug(var: Any, pretty: bool = True) -> str:
    """
    Pretty-print variable for debugging.

    Args:
        var: Variable to debug
        pretty: Use pretty printing (default: True)

    Returns:
        String representation of variable

    Example:
        {{ page | debug }}
        {{ config | debug(pretty=false) }}
    """
    if var is None:
        return "None"

    # Try to convert to dict if it has __dict__
    if hasattr(var, "__dict__") and not isinstance(var, type):
        var_dict = {k: v for k, v in var.__dict__.items() if not k.startswith("_")}
        var = var_dict

    if pretty:
        return pprint.pformat(var, indent=2, width=80)
    else:
        return str(var)


def typeof(var: Any) -> str:
    """
    Get the type of a variable.

    Args:
        var: Variable to check

    Returns:
        Type name as string

    Example:
        {{ page | typeof }}  # "Page"
        {{ "hello" | typeof }}  # "str"
    """
    return type(var).__name__


def inspect(obj: Any) -> str:
    """
    Inspect object attributes and methods.

    Args:
        obj: Object to inspect

    Returns:
        List of attributes and methods

    Example:
        {{ page | inspect }}
    """
    if obj is None:
        return "None"

    # Get all attributes
    attrs = dir(obj)

    # Filter out private attributes
    public_attrs = [attr for attr in attrs if not attr.startswith("_")]

    # Separate properties and methods
    properties = []
    methods = []

    for attr in public_attrs:
        try:
            value = getattr(obj, attr)
            if callable(value):
                methods.append(f"{attr}()")
            else:
                properties.append(attr)
        except Exception as e:
            logger.debug(
                "debug_function_getattr_failed",
                attr=attr,
                error=str(e),
                error_type=type(e).__name__,
                action="adding_as_property",
            )
            properties.append(attr)

    result = []
    if properties:
        result.append("Properties: " + ", ".join(sorted(properties)))
    if methods:
        result.append("Methods: " + ", ".join(sorted(methods)))

    return "\n".join(result)
