"""
Runtime capability resolution for opt-in heavy JS (Mermaid, KaTeX, Iconify).

Capabilities are config-gated (build-environment decision) and require
self-hosted vendor files under ``assets/vendor/`` (provisioned at build time
when enabled). Per-page asset emission is further gated by content detectors
(#571): a capability must be enabled, provisioned, AND needed on the page.

Registered capabilities are discovered from the ``bengal.capabilities`` entry-point
group (#572). Built-in diagram/math vendors ship as first-party registrations.

Note: the knowledge graph (minimap + /graph/ explorer) used to depend on D3 and
was gated here. It is now a dependency-free, first-party renderer with build-time
baked layout, so it is no longer a capability and ships by default.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.capabilities.registry import CapabilityRegistry


def _registry() -> CapabilityRegistry:
    from bengal.capabilities.registry import get_capability_registry

    return get_capability_registry()


def capability_names() -> frozenset[str]:
    """Names of all registered vendor capabilities."""
    return _registry().names


def __getattr__(name: str) -> Any:
    if name == "CAPABILITY_NAMES":
        return capability_names()
    if name == "VENDOR_FILES":
        registry = _registry()
        return {spec.name: spec.vendor_files for spec in registry}
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def _capabilities_config(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("capabilities")
    if not isinstance(raw, dict):
        return {}
    return raw


def is_capability_requested(config: dict[str, Any], name: str) -> bool:
    """True when the site config explicitly enables a registered capability."""
    if name not in _registry().names:
        return False
    return bool(_capabilities_config(config).get(name, False))


def vendor_dir_for_site(site_root: Path) -> Path:
    return site_root / "assets" / "vendor"


def vendors_present(vendor_dir: Path, name: str) -> bool:
    """True when all required vendor files exist on disk."""
    files = _registry().vendor_files(name)
    if not files:
        return False
    return all((vendor_dir / rel).is_file() for rel in files)


def resolve_runtime_capabilities(
    config: dict[str, Any],
    vendor_dir: Path | None = None,
) -> dict[str, bool]:
    """
    Resolve effective runtime capabilities: config flag AND vendor files present.

    Default build: all registered vendor capabilities False (zero external
    network requests at runtime). ``depends_on`` specs (e.g. iconify → mermaid)
    require their dependencies to also be active.
    """
    caps_cfg = _capabilities_config(config)
    vdir = vendor_dir or Path("assets/vendor")
    registry = _registry()

    active: dict[str, bool] = {}
    for spec in registry:
        if not caps_cfg.get(spec.name, False):
            active[spec.name] = False
            continue
        if not vendors_present(vdir, spec.name):
            active[spec.name] = False
            continue
        if any(not active.get(dep, False) for dep in spec.depends_on):
            active[spec.name] = False
            continue
        active[spec.name] = True

    return active
