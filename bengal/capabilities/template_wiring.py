"""Template wiring for page-scoped capability assets (#585)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bengal.capabilities.registry import CapabilityRegistry


def build_capability_wiring(
    effective: Mapping[str, bool],
    vendor_integrity: Mapping[str, str],
    *,
    registry: CapabilityRegistry | None = None,
) -> dict[str, Any]:
    """Build registry-driven asset wiring for the default theme."""
    from bengal.capabilities.registry import get_capability_registry

    registry = registry or get_capability_registry()
    active_names = sorted(name for name, enabled in effective.items() if enabled)

    stylesheets: list[dict[str, Any]] = []
    scripts: list[dict[str, Any]] = []
    lazy_loaders: list[dict[str, Any]] = []
    runtime_globals: list[dict[str, Any]] = []

    for name in active_names:
        spec = registry.get(name)
        if spec is None or spec.init is None:
            continue
        init = spec.init

        stylesheets.extend(
            {
                "path": f"vendor/{css_file}",
                "integrity": vendor_integrity.get(css_file),
            }
            for css_file in init.css_files
        )

        fetch_paths = {pack.rel_path for pack in init.runtime_fetch_assets}
        if init.lazy_selector:
            primary_asset = next(
                (asset for asset in spec.vendor_files if asset.endswith(".js")),
                spec.vendor_files[0] if spec.vendor_files else None,
            )
            if primary_asset:
                lazy_loaders.append(
                    {
                        "key": init.lazy_loader_key or spec.name,
                        "selector": init.lazy_selector,
                        "script": f"vendor/{primary_asset}",
                        "integrity": vendor_integrity.get(primary_asset),
                        "companions": list(init.companion_scripts),
                    }
                )
        else:
            scripts.extend(
                {
                    "path": f"vendor/{asset}",
                    "integrity": vendor_integrity.get(asset),
                    "defer": init.defer,
                }
                for asset in spec.vendor_files
                if asset not in init.css_files
                and asset not in fetch_paths
                and asset.endswith(".js")
            )
            scripts.extend(
                {
                    "path": companion,
                    "integrity": None,
                    "defer": True,
                }
                for companion in init.companion_scripts
            )

        if init.runtime_global and init.runtime_fetch_assets:
            runtime_globals.append(
                {
                    "name": init.runtime_global,
                    "packs": [
                        {"name": pack.name, "path": f"vendor/{pack.rel_path}"}
                        for pack in init.runtime_fetch_assets
                    ],
                }
            )

    return {
        "cache_key": "-".join(active_names),
        "stylesheets": stylesheets,
        "scripts": scripts,
        "lazy_loaders": lazy_loaders,
        "runtime_globals": runtime_globals,
    }


EMPTY_CAPABILITY_WIRING: dict[str, Any] = {
    "cache_key": "",
    "stylesheets": [],
    "scripts": [],
    "lazy_loaders": [],
    "runtime_globals": [],
}
