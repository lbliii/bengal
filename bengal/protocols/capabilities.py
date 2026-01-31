"""
Capability protocols for hasattr-style type narrowing.

This module provides Protocol definitions and TypeGuard functions for
safe capability checking. Instead of using `hasattr()` which doesn't
narrow types for ty, use these TypeGuard functions.

Usage:
    # Before (ty can't narrow after hasattr)
    if hasattr(engine, "clear_template_cache"):
        engine.clear_template_cache(names)  # Error: not callable

    # After (TypeGuard narrows the type)
    from bengal.protocols.capabilities import has_clear_template_cache

    if has_clear_template_cache(engine):
        engine.clear_template_cache(names)  # Works!

Thread Safety:
    All protocols are designed for use in multi-threaded contexts.
    TypeGuard functions are stateless and thread-safe.

"""

from __future__ import annotations

from typing import Any, Protocol, TypeGuard, runtime_checkable

# =============================================================================
# Template Engine Capabilities
# =============================================================================


@runtime_checkable
class HasClearTemplateCache(Protocol):
    """Protocol for objects with clear_template_cache method."""

    def clear_template_cache(self, names: list[str]) -> None:
        """Clear cached templates by name."""
        ...


def has_clear_template_cache(obj: object) -> TypeGuard[HasClearTemplateCache]:
    """
    TypeGuard for clear_template_cache capability.

    Use instead of hasattr() to enable type narrowing.

    Args:
        obj: Object to check

    Returns:
        True if obj has callable clear_template_cache method

    Example:
        if has_clear_template_cache(engine):
            engine.clear_template_cache(template_names)  # ty knows it's callable
    """
    return hasattr(obj, "clear_template_cache") and callable(
        getattr(obj, "clear_template_cache", None)
    )


# =============================================================================
# Dashboard/Screen Capabilities
# =============================================================================


@runtime_checkable
class HasActionRebuild(Protocol):
    """Protocol for objects with action_rebuild method."""

    def action_rebuild(self) -> None:
        """Trigger a rebuild action."""
        ...


def has_action_rebuild(obj: object) -> TypeGuard[HasActionRebuild]:
    """
    TypeGuard for action_rebuild capability.

    Args:
        obj: Object to check

    Returns:
        True if obj has callable action_rebuild method
    """
    return hasattr(obj, "action_rebuild") and callable(getattr(obj, "action_rebuild", None))


@runtime_checkable
class HasConfigChangedSignal(Protocol):
    """Protocol for objects with config_changed_signal property."""

    @property
    def config_changed_signal(self) -> object:
        """Signal emitted when config changes."""
        ...


def has_config_changed_signal(obj: object) -> TypeGuard[HasConfigChangedSignal]:
    """
    TypeGuard for config_changed_signal capability.

    Args:
        obj: Object to check

    Returns:
        True if obj has config_changed_signal attribute
    """
    return hasattr(obj, "config_changed_signal")


# =============================================================================
# Error Collection Capabilities
# =============================================================================


@runtime_checkable
class HasErrors(Protocol):
    """Protocol for objects with errors property."""

    @property
    def errors(self) -> list[Any]:
        """List of collected errors."""
        ...


def has_errors(obj: object) -> TypeGuard[HasErrors]:
    """
    TypeGuard for errors capability.

    Args:
        obj: Object to check

    Returns:
        True if obj has errors attribute
    """
    return hasattr(obj, "errors")


# =============================================================================
# Walk Capability (for page relationships)
# =============================================================================


@runtime_checkable
class HasWalk(Protocol):
    """Protocol for objects with walk method."""

    def walk(self) -> Any:
        """Walk the object hierarchy."""
        ...


def has_walk(obj: object) -> TypeGuard[HasWalk]:
    """
    TypeGuard for walk capability.

    Args:
        obj: Object to check

    Returns:
        True if obj has callable walk method
    """
    return hasattr(obj, "walk") and callable(getattr(obj, "walk", None))


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "HasActionRebuild",
    # Protocols
    "HasClearTemplateCache",
    "HasConfigChangedSignal",
    "HasErrors",
    "HasWalk",
    "has_action_rebuild",
    # TypeGuards
    "has_clear_template_cache",
    "has_config_changed_signal",
    "has_errors",
    "has_walk",
]
