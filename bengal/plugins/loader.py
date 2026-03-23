"""
Plugin discovery and loading via entry points.

Discovers installed plugins via the "bengal.plugins" entry point group,
instantiates them, validates they implement the Plugin protocol, and
runs registration. Returns a frozen registry ready for parallel rendering.

See bengal.core.theme.registry for the analogous theme entry point pattern.

"""

from __future__ import annotations

import importlib.metadata

from bengal.plugins.protocol import Plugin
from bengal.plugins.registry import FrozenPluginRegistry, PluginRegistry
from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)

ENTRY_POINT_GROUP = "bengal.plugins"


def discover_plugins() -> list[Plugin]:
    """Discover installed plugins via entry points."""
    plugins: list[Plugin] = []
    try:
        eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
    except TypeError:
        # Python < 3.12 compat
        eps = importlib.metadata.entry_points().get(ENTRY_POINT_GROUP, [])

    for ep in eps:
        try:
            plugin_cls = ep.load()
            plugin = plugin_cls() if isinstance(plugin_cls, type) else plugin_cls
            if isinstance(plugin, Plugin):
                plugins.append(plugin)
                logger.debug("plugin_discovered", name=ep.name, plugin=plugin.name)
            else:
                logger.warning(
                    "plugin_invalid",
                    name=ep.name,
                    reason="Does not implement Plugin protocol",
                )
        except Exception:
            logger.warning("plugin_load_failed", name=ep.name, exc_info=True)
    return plugins


def load_plugins(extra_plugins: list[Plugin] | None = None) -> FrozenPluginRegistry:
    """Discover, load, and register all plugins. Returns frozen registry.

    Args:
        extra_plugins: Additional plugins to register (e.g., from config)

    """
    registry = PluginRegistry()

    # Discover via entry points
    plugins = discover_plugins()

    # Add any explicitly provided plugins
    if extra_plugins:
        plugins.extend(extra_plugins)

    # Register all plugins
    for plugin in plugins:
        try:
            plugin.register(registry)
            logger.info("plugin_registered", name=plugin.name, version=plugin.version)
        except Exception:
            logger.error("plugin_register_failed", name=plugin.name, exc_info=True)

    frozen = registry.freeze()

    count = len(plugins)
    if count:
        logger.info("plugins_loaded", count=count)

    return frozen
