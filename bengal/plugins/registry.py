"""
Plugin registry: mutable builder and frozen immutable snapshot.

Follows the Builder->Immutable pattern established by
DirectiveRegistryBuilder/DirectiveRegistry.

PluginRegistry collects extensions during plugin registration,
then freeze() produces a FrozenPluginRegistry that is safe to
share across threads during parallel rendering.

"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.health.base import BaseValidator

logger = get_logger(__name__)


@dataclass
class FrozenPluginRegistry:
    """Immutable snapshot of all registered plugin extensions.

    Created by PluginRegistry.freeze(). Read-only during parallel rendering.

    """

    directives: tuple[Any, ...] = ()
    roles: tuple[Any, ...] = ()
    template_functions: tuple[tuple[str, Callable, int], ...] = ()  # (name, fn, phase)
    template_filters: tuple[tuple[str, Callable], ...] = ()
    template_tests: tuple[tuple[str, Callable], ...] = ()
    content_sources: tuple[tuple[str, type], ...] = ()
    health_validators: tuple[Any, ...] = ()
    shortcodes: tuple[tuple[str, str], ...] = ()  # (name, template_str)
    phase_hooks: tuple[tuple[str, Callable], ...] = ()  # (phase_name, callback)


class PluginRegistry:
    """Mutable registry for plugin extension registration.

    Plugins call methods on this registry during their register() phase.
    After all plugins register, freeze() produces an immutable FrozenPluginRegistry.

    Follows the Builder->Immutable pattern established by DirectiveRegistryBuilder.

    """

    __slots__ = (
        "_content_sources",
        "_directives",
        "_frozen",
        "_health_validators",
        "_phase_hooks",
        "_roles",
        "_shortcodes",
        "_template_filters",
        "_template_functions",
        "_template_tests",
    )

    def __init__(self) -> None:
        self._directives: list[Any] = []
        self._roles: list[Any] = []
        self._template_functions: list[tuple[str, Callable, int]] = []
        self._template_filters: list[tuple[str, Callable]] = []
        self._template_tests: list[tuple[str, Callable]] = []
        self._content_sources: list[tuple[str, type]] = []
        self._health_validators: list[Any] = []
        self._shortcodes: list[tuple[str, str]] = []
        self._phase_hooks: list[tuple[str, Callable]] = []
        self._frozen = False

    def _check_mutable(self) -> None:
        if self._frozen:
            msg = "Cannot modify a frozen PluginRegistry"
            raise RuntimeError(msg)

    def add_directive(self, handler: Any) -> None:
        """Register a directive handler (class with parse/render methods)."""
        self._check_mutable()
        self._directives.append(handler)

    def add_role(self, handler: Any) -> None:
        """Register a role handler (inline markup)."""
        self._check_mutable()
        self._roles.append(handler)

    def add_template_function(self, name: str, fn: Callable, *, phase: int = 1) -> None:
        """Register a template global function.

        Args:
            name: Function name in templates (e.g., "my_func")
            fn: The callable
            phase: Registration phase (1-9, matching template_functions phases)

        """
        self._check_mutable()
        self._template_functions.append((name, fn, phase))

    def add_template_filter(self, name: str, fn: Callable) -> None:
        """Register a template filter (value transformer)."""
        self._check_mutable()
        self._template_filters.append((name, fn))

    def add_template_test(self, name: str, fn: Callable) -> None:
        """Register a template test (boolean predicate)."""
        self._check_mutable()
        self._template_tests.append((name, fn))

    def add_content_source(self, name: str, source_cls: type) -> None:
        """Register a content source type."""
        self._check_mutable()
        self._content_sources.append((name, source_cls))

    def add_health_validator(self, validator: BaseValidator) -> None:
        """Register a health check validator."""
        self._check_mutable()
        self._health_validators.append(validator)

    def add_shortcode(self, name: str, template_str: str) -> None:
        """Register a shortcode template."""
        self._check_mutable()
        self._shortcodes.append((name, template_str))

    def on_phase(self, phase_name: str, callback: Callable) -> None:
        """Register a callback for a build phase.

        Args:
            phase_name: Phase identifier (e.g., "pre_render", "post_render")
            callback: Called with (site, build_context) when phase executes

        """
        self._check_mutable()
        self._phase_hooks.append((phase_name, callback))

    def freeze(self) -> FrozenPluginRegistry:
        """Produce an immutable snapshot. Registry becomes read-only."""
        self._frozen = True
        return FrozenPluginRegistry(
            directives=tuple(self._directives),
            roles=tuple(self._roles),
            template_functions=tuple(self._template_functions),
            template_filters=tuple(self._template_filters),
            template_tests=tuple(self._template_tests),
            content_sources=tuple(self._content_sources),
            health_validators=tuple(self._health_validators),
            shortcodes=tuple(self._shortcodes),
            phase_hooks=tuple(self._phase_hooks),
        )
