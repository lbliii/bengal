"""
Unified plugin system for Bengal SSG.

Provides a single registration interface for all extension points:
directives, roles, template functions/filters/tests, content sources,
health validators, shortcodes, and build phase hooks.

Follows the Builder->Immutable pattern established by DirectiveRegistryBuilder.

Example:
    >>> from bengal.plugins import Plugin, PluginRegistry, load_plugins
    >>> frozen = load_plugins()

"""

from contextvars import ContextVar, Token

from bengal.plugins.loader import load_plugins
from bengal.plugins.protocol import Plugin
from bengal.plugins.registry import FrozenPluginRegistry, PluginRegistry

__all__ = [
    "FrozenPluginRegistry",
    "Plugin",
    "PluginRegistry",
    "get_active_registry",
    "load_plugins",
    "reset_active_registry",
    "set_active_registry",
]

# Context-scoped holder for the frozen registry active during a build.
# Build parallelism uses context propagation, so worker threads inherit the
# registry for their build without sharing it with concurrent builds.
_active_registry: ContextVar[FrozenPluginRegistry | None] = ContextVar(
    "bengal_active_plugin_registry",
    default=None,
)


def set_active_registry(
    registry: FrozenPluginRegistry | None,
) -> Token[FrozenPluginRegistry | None]:
    """Set the active plugin registry for the current build."""
    return _active_registry.set(registry)


def reset_active_registry(token: Token[FrozenPluginRegistry | None]) -> None:
    """Restore the active plugin registry to a previous context value."""
    _active_registry.reset(token)


def get_active_registry() -> FrozenPluginRegistry | None:
    """Get the active plugin registry, or None if no plugins loaded."""
    return _active_registry.get()
