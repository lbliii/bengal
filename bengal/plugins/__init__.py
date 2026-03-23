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

from bengal.plugins.loader import load_plugins
from bengal.plugins.protocol import Plugin
from bengal.plugins.registry import FrozenPluginRegistry, PluginRegistry

__all__ = [
    "FrozenPluginRegistry",
    "Plugin",
    "PluginRegistry",
    "get_active_registry",
    "load_plugins",
    "set_active_registry",
]

# Module-level holder for the frozen registry active during a build.
# Set by BuildOrchestrator before Phase 1; read by template registration.
_active_registry: FrozenPluginRegistry | None = None


def set_active_registry(registry: FrozenPluginRegistry | None) -> None:
    """Set the active plugin registry for the current build."""
    global _active_registry
    _active_registry = registry


def get_active_registry() -> FrozenPluginRegistry | None:
    """Get the active plugin registry, or None if no plugins loaded."""
    return _active_registry
