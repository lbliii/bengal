"""
Supply-chain controls for capability vendor assets (#573).

Site owners can override download source (CDN vs local file), force a version
pin, and require SRI verification. Computed integrity hashes are exposed to
templates for ``integrity`` attributes on script/link tags.
"""

from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlparse

if TYPE_CHECKING:
    from collections.abc import Mapping

SourceMode = Literal["cdn", "local"]

# Default upstream pins (author-owned; overridable by site owner).
DEFAULT_PINS: dict[str, str] = {
    "mermaid": "10",
    "katex": "0.16.11",
    "iconify": "1",
}

# Pinned SRI for known vendor files (sha384). Verified on CDN download when enabled.
# Local copies skip remote verification but still emit integrity when bytes are known.
VENDOR_SRI: dict[str, dict[str, str]] = {
    "mermaid": {},
    "katex": {},
    "iconify": {},
}


@dataclass(frozen=True, slots=True)
class CapabilitySourceOverride:
    """Per-capability owner override from [capabilities.sources.<name>]."""

    source: SourceMode = "cdn"
    local_path: Path | None = None
    pin: str | None = None
    sri: str | None = None
    require_sri: bool = True


@dataclass(frozen=True, slots=True)
class ResolvedVendorAsset:
    """Resolved provisioning spec for one vendor file."""

    capability: str
    rel_path: str
    source_mode: SourceMode
    url: str | None
    local_path: Path | None
    expected_sri: str | None
    require_sri: bool


def compute_sri(data: bytes, *, algorithm: str = "sha384") -> str:
    """Return an ``integrity`` attribute value (e.g. ``sha384-...``)."""
    digest = hashlib.new(algorithm, data).digest()
    encoded = base64.b64encode(digest).decode("ascii")
    return f"{algorithm}-{encoded}"


def verify_sri(data: bytes, expected: str) -> bool:
    """Verify bytes against an ``integrity`` attribute value."""
    if not expected or "-" not in expected:
        return False
    algorithm, _encoded = expected.split("-", 1)
    return compute_sri(data, algorithm=algorithm) == expected


def _capability_sources_config(config: Mapping[str, Any]) -> dict[str, Any]:
    caps = config.get("capabilities")
    if not isinstance(caps, dict):
        return {}
    sources = caps.get("sources")
    return sources if isinstance(sources, dict) else {}


def parse_capability_override(
    config: Mapping[str, Any],
    capability: str,
) -> CapabilitySourceOverride:
    """Parse owner override for a capability from config."""
    raw = _capability_sources_config(config).get(capability)
    if not isinstance(raw, dict):
        return CapabilitySourceOverride()

    source_raw = str(raw.get("source", "cdn")).strip().lower()
    source: SourceMode = "local" if source_raw == "local" else "cdn"

    local_path: Path | None = None
    if raw.get("path"):
        local_path = Path(str(raw["path"]))
    elif raw.get("local_path"):
        local_path = Path(str(raw["local_path"]))

    pin = str(raw["pin"]).strip() if raw.get("pin") else None
    sri = str(raw["sri"]).strip() if raw.get("sri") else None
    require_sri = bool(raw.get("require_sri", True))

    return CapabilitySourceOverride(
        source=source,
        local_path=local_path,
        pin=pin,
        sri=sri,
        require_sri=require_sri,
    )


def _apply_pin_to_url(url: str, pin: str) -> str:
    """Substitute version pin placeholders or semver segments in a template URL."""
    if "{pin}" in url:
        return url.replace("{pin}", pin)
    # jsdelivr: .../npm/mermaid@10/dist/... or .../katex@0.16.11/dist/...
    return re.sub(r"@[^/]+/", f"@{pin}/", url, count=1)


def resolve_vendor_asset(
    config: Mapping[str, Any],
    capability: str,
    rel_path: str,
    default_url: str,
    *,
    site_root: Path | None = None,
) -> ResolvedVendorAsset:
    """Resolve how to provision one vendor file (CDN download or local copy)."""
    override = parse_capability_override(config, capability)
    pin = override.pin or DEFAULT_PINS.get(capability, "")
    url = _apply_pin_to_url(default_url, pin) if pin else default_url

    expected_sri = override.sri or VENDOR_SRI.get(capability, {}).get(rel_path)

    local_path = override.local_path
    if local_path and not local_path.is_absolute() and site_root is not None:
        local_path = site_root / local_path

    if override.source == "local":
        if local_path is None:
            msg = f"capabilities.sources.{capability}.path required when source=local"
            raise ValueError(msg)
        return ResolvedVendorAsset(
            capability=capability,
            rel_path=rel_path,
            source_mode="local",
            url=None,
            local_path=local_path,
            expected_sri=expected_sri,
            require_sri=override.require_sri,
        )

    # CDN mode — optional local_path is ignored; fetch from resolved URL.
    if not urlparse(url).scheme:
        msg = f"Invalid vendor URL for {capability}/{rel_path}: {url!r}"
        raise ValueError(msg)

    return ResolvedVendorAsset(
        capability=capability,
        rel_path=rel_path,
        source_mode="cdn",
        url=url,
        local_path=None,
        expected_sri=expected_sri,
        require_sri=override.require_sri,
    )


def record_vendor_integrity(
    store: dict[str, str],
    rel_path: str,
    data: bytes,
    *,
    expected_sri: str | None = None,
    require_sri: bool = True,
) -> str:
    """
    Verify optional expected SRI, compute integrity hash, and record for templates.

    Returns the integrity attribute value.
    """
    if expected_sri and require_sri and not verify_sri(data, expected_sri):
        msg = f"SRI mismatch for {rel_path}"
        raise ValueError(msg)
    integrity = compute_sri(data)
    store[rel_path] = integrity
    return integrity
