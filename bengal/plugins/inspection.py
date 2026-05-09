"""Plugin discovery inspection for CLI and tests."""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from bengal.plugins.loader import ENTRY_POINT_GROUP
from bengal.plugins.protocol import Plugin
from bengal.plugins.registry import FrozenPluginRegistry, PluginRegistry

CAPABILITY_FIELDS = (
    "directives",
    "roles",
    "template_functions",
    "template_filters",
    "template_tests",
    "content_sources",
    "health_validators",
    "shortcodes",
    "phase_hooks",
)

# Whether each registered plugin capability is currently wired into builds.
CAPABILITY_INTEGRATION_STATUS = MappingProxyType(
    {
        "directives": "ready",
        "roles": "ready",
        "template_functions": "ready",
        "template_filters": "ready",
        "template_tests": "ready",
        "content_sources": "pending",
        "health_validators": "pending",
        "shortcodes": "pending",
        "phase_hooks": "ready",
    }
)

CAPABILITY_NOTES = MappingProxyType(
    {
        "directives": "Applied to the Patitas directive registry during parser setup.",
        "roles": "Applied to the Patitas role registry during parser setup.",
        "template_functions": "Applied to template environments during registration.",
        "template_filters": "Applied to template environments during registration.",
        "template_tests": "Applied to template environments during registration.",
        "content_sources": "Registered, but content source discovery is not wired yet.",
        "health_validators": "Registered, but health validator injection is not wired yet.",
        "shortcodes": "Registered, but shortcode registry injection is not wired yet.",
        "phase_hooks": "Executed by build lifecycle phase hooks.",
    }
)


@dataclass(frozen=True, slots=True)
class PluginInspection:
    """Result of inspecting one plugin entry point."""

    entry_point: str
    value: str
    plugin_name: str | None = None
    version: str | None = None
    status: str = "unknown"
    capabilities: dict[str, int] = field(default_factory=dict)
    errors: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        """True when the plugin loads, registers, and uses only wired capabilities."""
        return self.status == "ready"

    @property
    def has_load_error(self) -> bool:
        """True when the plugin failed to load from its entry point."""
        return self.status == "load_error"

    @property
    def pending_capabilities(self) -> tuple[str, ...]:
        """Capabilities this plugin registers that Bengal does not wire yet."""
        return tuple(
            name
            for name, count in self.capabilities.items()
            if count and CAPABILITY_INTEGRATION_STATUS.get(name) != "ready"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize for CLI structured output."""
        return {
            "entry_point": self.entry_point,
            "value": self.value,
            "name": self.plugin_name,
            "version": self.version,
            "status": self.status,
            "ready": self.ready,
            "capabilities": self.capabilities,
            "pending_capabilities": list(self.pending_capabilities),
            "errors": list(self.errors),
        }


def capability_counts(registry: FrozenPluginRegistry) -> dict[str, int]:
    """Return per-capability counts from a frozen plugin registry."""
    return {field_name: len(getattr(registry, field_name)) for field_name in CAPABILITY_FIELDS}


def capability_details(counts: dict[str, int]) -> list[dict[str, Any]]:
    """Return capability count plus integration readiness details."""
    details: list[dict[str, Any]] = []
    for name in CAPABILITY_FIELDS:
        count = counts.get(name, 0)
        status = CAPABILITY_INTEGRATION_STATUS[name]
        details.append(
            {
                "name": name,
                "count": count,
                "integration_status": status,
                "ready": count == 0 or status == "ready",
                "note": CAPABILITY_NOTES[name],
            }
        )
    return details


def _entry_points() -> list[Any]:
    """Return entry points for the Bengal plugin group."""
    try:
        return list(importlib.metadata.entry_points(group=ENTRY_POINT_GROUP))
    except TypeError:
        return list(importlib.metadata.entry_points().get(ENTRY_POINT_GROUP, []))


def inspect_entry_point(entry_point: Any) -> PluginInspection:
    """Load and validate one plugin entry point without mutating global state."""
    entry_name = str(getattr(entry_point, "name", "<unknown>"))
    entry_value = str(getattr(entry_point, "value", ""))
    try:
        plugin_obj = entry_point.load()
        plugin = plugin_obj() if isinstance(plugin_obj, type) else plugin_obj
    except Exception as exc:
        return PluginInspection(
            entry_point=entry_name,
            value=entry_value,
            status="load_error",
            errors=(f"{type(exc).__name__}: {exc}",),
        )

    plugin_name = str(getattr(plugin, "name", entry_name))
    version = str(getattr(plugin, "version", "unknown"))

    if not isinstance(plugin, Plugin):
        return PluginInspection(
            entry_point=entry_name,
            value=entry_value,
            plugin_name=plugin_name,
            version=version,
            status="invalid",
            errors=("Does not implement bengal.plugins.Plugin",),
        )

    registry = PluginRegistry()
    try:
        plugin.register(registry)
    except Exception as exc:
        return PluginInspection(
            entry_point=entry_name,
            value=entry_value,
            plugin_name=plugin_name,
            version=version,
            status="register_error",
            errors=(f"{type(exc).__name__}: {exc}",),
        )

    counts = capability_counts(registry.freeze())
    status = (
        "partial"
        if any(
            counts[name] and CAPABILITY_INTEGRATION_STATUS[name] != "ready"
            for name in CAPABILITY_FIELDS
        )
        else "ready"
    )

    return PluginInspection(
        entry_point=entry_name,
        value=entry_value,
        plugin_name=plugin_name,
        version=version,
        status=status,
        capabilities=counts,
    )


def inspect_installed_plugins() -> list[PluginInspection]:
    """Inspect all installed Bengal plugin entry points."""
    return [inspect_entry_point(entry_point) for entry_point in _entry_points()]
