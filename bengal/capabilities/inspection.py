"""Runtime capability inspection for CLI and tests (#588)."""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bengal.capabilities.registry import ENTRY_POINT_GROUP, get_capability_registry
from bengal.capabilities.runtime import (
    is_capability_requested,
    vendor_dir_for_site,
    vendors_present,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from bengal.capabilities.spec import CapabilitySpec


@dataclass(frozen=True, slots=True)
class CapabilityInspection:
    """Inspection report for one registered runtime capability."""

    name: str
    entry_point: str | None = None
    distribution: str | None = None
    version: str | None = None
    origin: str = "builtin"
    spec: CapabilitySpec | None = None
    enabled_in_config: bool | None = None
    vendors_present: bool | None = None
    errors: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        spec = self.spec
        return {
            "name": self.name,
            "entry_point": self.entry_point,
            "distribution": self.distribution,
            "version": self.version,
            "origin": self.origin,
            "enabled_in_config": self.enabled_in_config,
            "vendors_present": self.vendors_present,
            "errors": list(self.errors),
            "assets": list(spec.vendor_files) if spec else [],
            "fence_languages": list(spec.fence_languages) if spec else [],
            "depends_on": list(spec.depends_on) if spec else [],
            "implies": list(spec.implies) if spec else [],
            "default_pin": spec.default_pin if spec else None,
            "has_init": spec.init is not None if spec else False,
        }


def _entry_points() -> list[importlib.metadata.EntryPoint]:
    try:
        return list(importlib.metadata.entry_points(group=ENTRY_POINT_GROUP))
    except TypeError:
        return list(importlib.metadata.entry_points().get(ENTRY_POINT_GROUP, []))


def _distribution_for(entry_point: importlib.metadata.EntryPoint) -> tuple[str | None, str | None]:
    dist_obj = entry_point.dist
    if not dist_obj:
        return None, None
    if hasattr(dist_obj, "metadata"):
        meta = dist_obj.metadata
        name = meta.get("Name") if hasattr(meta, "get") else getattr(meta, "Name", None)
        version = getattr(dist_obj, "version", None)
        return name, version
    if isinstance(dist_obj, str):
        try:
            dist = importlib.metadata.distribution(dist_obj)
        except importlib.metadata.PackageNotFoundError:
            return dist_obj, None
        return dist.metadata["Name"], dist.version
    return None, None


def inspect_capabilities(
    *,
    config: Mapping[str, Any] | None = None,
    site_root: Path | None = None,
) -> list[CapabilityInspection]:
    """Inspect all registered runtime capabilities."""
    registry = get_capability_registry()
    entry_by_name = {ep.name: ep for ep in _entry_points()}
    reports: list[CapabilityInspection] = []

    for spec in registry:
        entry_point = entry_by_name.get(spec.name)
        distribution = version = None
        origin = "third-party" if entry_point else "builtin"
        entry_name = entry_point.name if entry_point else None
        if entry_point:
            distribution, version = _distribution_for(entry_point)

        enabled = vendors_ok = None
        if config is not None:
            enabled = is_capability_requested(config, spec.name)
            if site_root is not None:
                vendors_ok = vendors_present(vendor_dir_for_site(site_root), spec.name)

        reports.append(
            CapabilityInspection(
                name=spec.name,
                entry_point=entry_name,
                distribution=distribution,
                version=version,
                origin=origin,
                spec=spec,
                enabled_in_config=enabled,
                vendors_present=vendors_ok,
            )
        )

    return reports


def validate_capability_config(
    config: Mapping[str, Any],
    *,
    site_root: Path | None = None,
) -> list[dict[str, str]]:
    """Return config/site issues for runtime capabilities."""
    issues: list[dict[str, str]] = []
    registry = get_capability_registry()
    caps_cfg = config.get("capabilities")
    if not isinstance(caps_cfg, dict):
        return issues

    known = registry.names
    for key, value in caps_cfg.items():
        if key in {"sources", "policy"}:
            continue
        if key not in known:
            issues.append(
                {
                    "level": "warning",
                    "message": (
                        f"Unknown capability {key!r} in [capabilities] — "
                        f"known: {', '.join(sorted(known))}"
                    ),
                }
            )
            continue
        if (
            value
            and site_root is not None
            and not vendors_present(vendor_dir_for_site(site_root), key)
        ):
            issues.append(
                {
                    "level": "warning",
                    "message": (
                        f"Capability {key!r} is enabled but vendor files are missing "
                        f"under assets/vendor/"
                    ),
                }
            )

    sources = caps_cfg.get("sources")
    if isinstance(sources, dict):
        issues.extend(
            {
                "level": "warning",
                "message": (
                    f"Unknown capability {source_name!r} in "
                    "[capabilities.sources] — no matching registry entry"
                ),
            }
            for source_name in sources
            if source_name not in known
        )

    return issues
