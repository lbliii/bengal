"""
Engine-agnostic adapter layer for template functions.

This module provides adapters that bridge pure Python template functions
to engine-specific mechanisms (like Jinja2's @pass_context).

Architecture:
Template functions are pure Python functions that take explicit parameters.
Adapters wrap these functions for each engine's context mechanism:

- Jinja2: Uses @pass_context decorator to extract page from ctx
- Kida: Uses render-time context injection
- Generic: For unknown engines, provides page as explicit parameter

Usage:
The adapter is automatically detected based on the environment type,
or can be explicitly specified in site configuration:

    rendering:
      adapter: kida

Example:
    >>> from bengal.rendering.adapters import get_adapter_type, register_context_functions
    >>> adapter_type = get_adapter_type(env, site)
    >>> register_context_functions(env, site, adapter_type)

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.protocols import SiteLike


def detect_adapter_type(env: Any) -> str:
    """Auto-detect engine type from environment class.

    Uses class name inspection as primary detection method.

    Args:
        env: Template environment instance (Jinja2, Kida, etc.)

    Returns:
        Engine type string: "jinja", "kida", or "generic"

    """
    class_name = type(env).__name__.lower()
    module_name = type(env).__module__.lower() if hasattr(type(env), "__module__") else ""

    # Check for Jinja2 environment
    if "jinja" in class_name or "jinja" in module_name:
        return "jinja"
    # Jinja2's Environment class is just called "Environment"
    if class_name == "environment" and "jinja2" in module_name:
        return "jinja"

    # Check for Kida environment
    if "kida" in class_name or "kida" in module_name:
        return "kida"

    return "generic"


def get_adapter_type(env: Any, site: SiteLike) -> str:
    """Get adapter type with config override support.

    Args:
        env: Template environment instance
        site: Site instance for configuration

    Returns:
        Engine type string

    Config example:
        rendering:
          adapter: kida  # Explicit override

    """
    # Check for explicit config override
    rendering_config = site.config.get("rendering", {}) if hasattr(site.config, "get") else {}
    if isinstance(rendering_config, dict):
        config_adapter = rendering_config.get("adapter")
        if config_adapter:
            return str(config_adapter)

    # Auto-detect from environment
    return detect_adapter_type(env)


def register_context_functions(env: Any, site: SiteLike, adapter_type: str | None = None) -> None:
    """Register context-dependent template functions using the appropriate adapter.

    These functions need access to the current page context (e.g., for i18n).
    Non-context functions are registered directly by their modules.

    Args:
        env: Template environment instance
        site: Site instance
        adapter_type: Engine type (auto-detected if None)

    """
    if adapter_type is None:
        adapter_type = get_adapter_type(env, site)

    if adapter_type == "jinja":
        from bengal.rendering.adapters.jinja import register_context_functions as jinja_register

        jinja_register(env, site)
    elif adapter_type == "kida":
        from bengal.rendering.adapters.kida import register_context_functions as kida_register

        kida_register(env, site)
    else:
        from bengal.rendering.adapters.generic import (
            register_context_functions as generic_register,
        )

        generic_register(env, site)


__all__ = [
    "detect_adapter_type",
    "get_adapter_type",
    "register_context_functions",
]
