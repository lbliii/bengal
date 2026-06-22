"""
Capability registry populated from ``bengal.capabilities`` entry points (#572).

Built-in diagram/math capabilities register via ``pyproject.toml``; third-party
packages add their own entry points without editing core.
"""

from __future__ import annotations

import importlib.metadata
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bengal.capabilities.spec import CapabilitySpec
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    import re
    from collections.abc import Iterable, Iterator

logger = get_logger(__name__)

ENTRY_POINT_GROUP = "bengal.capabilities"

_registry_lock = threading.Lock()
_cached_registry: CapabilityRegistry | None = None


@dataclass(frozen=True, slots=True)
class CapabilityRegistry:
    """Immutable registry of discovered capability specs."""

    specs: tuple[CapabilitySpec, ...]
    _by_name: dict[str, CapabilitySpec]
    _html_patterns: dict[str, tuple[re.Pattern[str], ...]]
    _source_patterns: dict[str, tuple[re.Pattern[str], ...]]
    _fence_languages: dict[str, CapabilitySpec]

    @classmethod
    def from_specs(cls, specs: Iterable[CapabilitySpec]) -> CapabilityRegistry:
        ordered = _validate_and_order(list(specs))
        by_name = {spec.name: spec for spec in ordered}
        html_patterns = {spec.name: spec.compiled_html_patterns() for spec in ordered}
        source_patterns = {spec.name: spec.compiled_source_patterns() for spec in ordered}
        fence_languages = _build_fence_language_index(ordered)
        return cls(
            specs=tuple(ordered),
            _by_name=by_name,
            _html_patterns=html_patterns,
            _source_patterns=source_patterns,
            _fence_languages=fence_languages,
        )

    @property
    def names(self) -> frozenset[str]:
        return frozenset(self._by_name)

    def get(self, name: str) -> CapabilitySpec | None:
        return self._by_name.get(name)

    def __iter__(self) -> Iterator[CapabilitySpec]:
        return iter(self.specs)

    def vendor_files(self, name: str) -> tuple[str, ...]:
        spec = self.get(name)
        return spec.vendor_files if spec else ()

    def vendor_urls(self, name: str) -> dict[str, str]:
        spec = self.get(name)
        return spec.vendor_urls if spec else {}

    def default_pins(self) -> dict[str, str]:
        return {spec.name: spec.default_pin for spec in self.specs}

    def html_patterns(self, name: str) -> tuple[re.Pattern[str], ...]:
        return self._html_patterns.get(name, ())

    def source_patterns(self, name: str) -> tuple[re.Pattern[str], ...]:
        return self._source_patterns.get(name, ())

    def fence_spec_for_language(self, language: str) -> CapabilitySpec | None:
        return self._fence_languages.get(language.lower())


def _build_fence_language_index(specs: list[CapabilitySpec]) -> dict[str, CapabilitySpec]:
    index: dict[str, CapabilitySpec] = {}
    for spec in specs:
        render = spec.resolved_fence_render()
        if render is None:
            continue
        for language in spec.fence_languages:
            key = language.lower()
            if key in index:
                existing = index[key].name
                msg = (
                    f"Duplicate fence language {language!r} registered by "
                    f"{existing!r} and {spec.name!r}"
                )
                raise ValueError(msg)
            index[key] = spec
    return index


def _validate_and_order(specs: list[CapabilitySpec]) -> list[CapabilitySpec]:
    if not specs:
        msg = "Capability registry is empty — at least one spec is required"
        raise ValueError(msg)

    seen: set[str] = set()
    for spec in specs:
        if spec.name in seen:
            msg = f"Duplicate capability registration: {spec.name!r}"
            raise ValueError(msg)
        seen.add(spec.name)

    by_name = {spec.name: spec for spec in specs}
    for spec in specs:
        for dep in (*spec.depends_on, *spec.implies):
            if dep not in by_name:
                msg = f"Capability {spec.name!r} references unknown capability {dep!r}"
                raise ValueError(msg)

    for spec in specs:
        if spec.fence_languages and spec.resolved_fence_render() is None:
            msg = f"Capability {spec.name!r} declares fence_languages but no fence_render contract"
            raise ValueError(msg)

    implied_names = {name for spec in specs for name in spec.implies}
    for spec in specs:
        if not spec.has_content_detector() and spec.name not in implied_names:
            msg = (
                f"Capability {spec.name!r} needs content detectors or must be "
                "listed in another capability's ``implies``"
            )
            raise ValueError(msg)

    # Stable ordering: dependencies before dependents.
    ordered: list[CapabilitySpec] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            msg = f"Cycle in capability dependencies involving {name!r}"
            raise ValueError(msg)
        visiting.add(name)
        spec = by_name[name]
        for dep in spec.depends_on:
            visit(dep)
        visiting.remove(name)
        visited.add(name)
        ordered.append(spec)

    for spec in sorted(specs, key=lambda s: s.name):
        visit(spec.name)

    return ordered


def _entry_points() -> list[importlib.metadata.EntryPoint]:
    try:
        return list(importlib.metadata.entry_points(group=ENTRY_POINT_GROUP))
    except TypeError:
        return list(importlib.metadata.entry_points().get(ENTRY_POINT_GROUP, []))


def _load_spec(entry_point: importlib.metadata.EntryPoint) -> CapabilitySpec:
    loaded = entry_point.load()
    if callable(loaded) and not isinstance(loaded, CapabilitySpec):
        loaded = loaded()
    if not isinstance(loaded, CapabilitySpec):
        msg = (
            f"Entry point {entry_point.name!r} must resolve to a CapabilitySpec, "
            f"got {type(loaded).__name__}"
        )
        raise TypeError(msg)
    if loaded.name != entry_point.name:
        logger.warning(
            "capability_entry_point_name_mismatch",
            entry_point=entry_point.name,
            spec_name=loaded.name,
        )
    return loaded


def discover_capability_specs() -> list[CapabilitySpec]:
    """Discover capability specs from installed entry points."""
    specs: list[CapabilitySpec] = []
    for ep in _entry_points():
        try:
            specs.append(_load_spec(ep))
            logger.debug("capability_discovered", name=ep.name)
        except Exception:
            logger.warning("capability_load_failed", name=ep.name, exc_info=True)

    if not specs:
        from bengal.capabilities.builtins import BUILTIN_CAPABILITIES

        specs = list(BUILTIN_CAPABILITIES)
        logger.debug("capability_registry_using_builtins", count=len(specs))

    return specs


def load_capability_registry(
    *,
    extra_specs: Iterable[CapabilitySpec] | None = None,
) -> CapabilityRegistry:
    """Load and validate the capability registry from entry points."""
    specs = discover_capability_specs()
    if extra_specs:
        specs.extend(extra_specs)
    return CapabilityRegistry.from_specs(specs)


def get_capability_registry() -> CapabilityRegistry:
    """Return the cached capability registry (thread-safe singleton)."""
    global _cached_registry
    if _cached_registry is not None:
        return _cached_registry
    with _registry_lock:
        if _cached_registry is None:
            _cached_registry = load_capability_registry()
        return _cached_registry


def reset_capability_registry(
    registry: CapabilityRegistry | None = None,
) -> None:
    """Reset cached registry (tests only)."""
    global _cached_registry
    with _registry_lock:
        _cached_registry = registry
