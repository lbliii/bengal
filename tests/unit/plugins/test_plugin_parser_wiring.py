"""Tests for plugin directive and role wiring into Patitas parser registries."""

from __future__ import annotations

from typing import ClassVar

from bengal.parsing import PatitasParser
from bengal.parsing.backends.patitas.directives.registry import create_default_registry
from bengal.parsing.backends.patitas.roles.registry import (
    create_default_registry as create_default_role_registry,
)
from bengal.plugins import set_active_registry
from bengal.plugins.registry import PluginRegistry


class PluginDirective:
    names: ClassVar[tuple[str, ...]] = ("plugin-note",)
    token_type: ClassVar[str] = "plugin_note"


class PluginRole:
    names: ClassVar[tuple[str, ...]] = ("plugin-role",)
    token_type: ClassVar[str] = "plugin_role"


def _plugin_registry():
    registry = PluginRegistry()
    registry.add_directive(PluginDirective())
    registry.add_role(PluginRole())
    return registry.freeze()


def test_plugin_directives_are_added_to_default_registry() -> None:
    registry = create_default_registry(plugin_registry=_plugin_registry())

    assert registry.get("plugin-note") is not None
    assert registry.get_by_token_type("plugin_note") is not None


def test_plugin_roles_are_added_to_default_registry() -> None:
    registry = create_default_role_registry(plugin_registry=_plugin_registry())

    assert registry.get("plugin-role") is not None
    assert registry.get_by_token_type("plugin_role") is not None


def test_patitas_parser_uses_active_plugin_registry() -> None:
    set_active_registry(_plugin_registry())
    try:
        parser = PatitasParser(enable_highlighting=False)
    finally:
        set_active_registry(None)

    assert parser._md._parse_config.directive_registry.get("plugin-note") is not None
    assert parser._md._render_config.role_registry.get("plugin-role") is not None
