"""
Plugin protocol for Bengal extensions.

Defines the interface that all Bengal plugins must implement.
Uses runtime_checkable Protocol for entry point validation.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.plugins.registry import PluginRegistry


@runtime_checkable
class Plugin(Protocol):
    """Unified plugin interface for Bengal extensions.

    Plugins register their extensions (directives, template functions,
    themes, content sources, etc.) through a single register() call.
    The registry is frozen before parallel rendering begins.

    """

    name: str
    version: str

    def register(self, registry: PluginRegistry) -> None:
        """Register all extensions this plugin provides."""
        ...
