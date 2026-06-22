"""
Runtime capability resolution for opt-in heavy JS (Mermaid, KaTeX, Iconify).

Capabilities are config-gated (build-environment decision) and require
self-hosted vendor files under ``assets/vendor/`` (provisioned at build time
when enabled). Per-page asset emission is further gated by content detectors
(#571): a capability must be enabled, provisioned, AND needed on the page.

Note: the knowledge graph (minimap + /graph/ explorer) used to depend on D3 and
was gated here. It is now a dependency-free, first-party renderer with build-time
baked layout, so it is no longer a capability and ships by default.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

CAPABILITY_NAMES = frozenset({"mermaid", "katex", "iconify"})

# Vendor files written by CapabilityVendorHelper (relative to assets/vendor/).
VENDOR_FILES: dict[str, tuple[str, ...]] = {
    "mermaid": ("mermaid.min.js",),
    "katex": ("katex.min.js", "katex.min.css"),
    "iconify": (
        "iconify/fa.json",
        "iconify/mdi.json",
        "iconify/logos.json",
    ),
}


def _capabilities_config(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("capabilities")
    if not isinstance(raw, dict):
        return {}
    return raw


def is_capability_requested(config: dict[str, Any], name: str) -> bool:
    """True when the site config explicitly enables a capability."""
    if name not in CAPABILITY_NAMES:
        return False
    return bool(_capabilities_config(config).get(name, False))


def vendor_dir_for_site(site_root: Path) -> Path:
    return site_root / "assets" / "vendor"


def vendors_present(vendor_dir: Path, name: str) -> bool:
    """True when all required vendor files exist on disk."""
    files = VENDOR_FILES.get(name)
    if not files:
        return False
    return all((vendor_dir / rel).is_file() for rel in files)


def resolve_runtime_capabilities(
    config: dict[str, Any],
    vendor_dir: Path | None = None,
) -> dict[str, bool]:
    """
    Resolve effective runtime capabilities: config flag AND vendor files present.

    Default build: all False (zero external network requests at runtime).
    """
    caps_cfg = _capabilities_config(config)
    vdir = vendor_dir or Path("assets/vendor")

    def _active(name: str) -> bool:
        if not caps_cfg.get(name, False):
            return False
        return vendors_present(vdir, name)

    mermaid = _active("mermaid")
    return {
        "mermaid": mermaid,
        "katex": _active("katex"),
        # Iconify packs are only meaningful alongside Mermaid diagram icons.
        "iconify": mermaid and _active("iconify"),
    }
