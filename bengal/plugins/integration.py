"""
Integration helpers to wire FrozenPluginRegistry into existing subsystems.

Each function applies one category of plugin extensions to the appropriate
Bengal subsystem (directive builder, template environment, etc.).

Currently wired:
- Template extensions (functions, filters, tests) — via register_all() in
  bengal.rendering.template_functions

Scaffolding for future subsystem integration:
- Directives and roles — pending directive/role builder plugin hooks
- Content sources — pending content source registry plugin hooks
- Phase hooks — pending build orchestrator phase hook wiring

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.plugins.registry import FrozenPluginRegistry

logger = get_logger(__name__)


def apply_plugin_directives(frozen: FrozenPluginRegistry, directive_builder: Any) -> None:
    """Register plugin directives into the directive registry builder."""
    for handler in frozen.directives:
        try:
            directive_builder.register(handler)
        except Exception:
            logger.warning("plugin_directive_failed", handler=type(handler).__name__, exc_info=True)


def apply_plugin_roles(frozen: FrozenPluginRegistry, role_builder: Any) -> None:
    """Register plugin roles into the role registry builder."""
    for handler in frozen.roles:
        try:
            role_builder.register(handler)
        except Exception:
            logger.warning("plugin_role_failed", handler=type(handler).__name__, exc_info=True)


def apply_plugin_template_extensions(frozen: FrozenPluginRegistry, env: Any, site: Any) -> None:
    """Register plugin template functions, filters, and tests."""
    for name, fn, _phase in frozen.template_functions:
        env.globals[name] = fn

    for name, fn in frozen.template_filters:
        env.filters[name] = fn

    for name, fn in frozen.template_tests:
        env.tests[name] = fn


def apply_plugin_content_sources(
    frozen: FrozenPluginRegistry, source_registry: dict[str, type]
) -> None:
    """Register plugin content sources."""
    source_registry.update(dict(frozen.content_sources))


def apply_plugin_phase_hooks(
    frozen: FrozenPluginRegistry, phase_name: str, site: Any, context: Any = None
) -> None:
    """Execute plugin phase hooks for a given phase."""
    for hook_phase, callback in frozen.phase_hooks:
        if hook_phase == phase_name:
            try:
                callback(site, context)
            except Exception:
                logger.warning("plugin_hook_failed", phase=phase_name, exc_info=True)
