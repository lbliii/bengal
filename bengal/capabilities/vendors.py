"""
Build-time vendor provisioning for opt-in diagram/math capabilities.

Downloads pinned vendor assets into ``assets/vendor/`` when a capability is
enabled in config. Network I/O happens at build time only — runtime output
uses self-hosted same-origin URLs.

Supply-chain controls (#573): SRI verification, CDN/local source override,
and version pin override via ``[capabilities.sources.<name>]``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bengal import __version__ as BENGAL_VERSION
from bengal.capabilities.runtime import (
    VENDOR_FILES,
    is_capability_requested,
    vendor_dir_for_site,
)
from bengal.capabilities.supply_chain import (
    record_vendor_integrity,
    resolve_vendor_asset,
)
from bengal.fonts.utils import urlopen_with_ssl_fallback
from bengal.utils.io.atomic_write import atomic_write_bytes
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

logger = get_logger(__name__)

_VENDOR_USER_AGENT = f"Bengal/{BENGAL_VERSION} (capability-vendor-provisioning)"
_INTEGRITY_MANIFEST = ".capability-integrity.json"

# Pinned upstream URL templates — fetched at build time only, never referenced in HTML output.
# ``{pin}`` is substituted from DEFAULT_PINS or owner override.
VENDOR_SOURCES: dict[str, dict[str, str]] = {
    "mermaid": {
        "mermaid.min.js": "https://cdn.jsdelivr.net/npm/mermaid@{pin}/dist/mermaid.min.js",
    },
    "katex": {
        "katex.min.js": "https://cdn.jsdelivr.net/npm/katex@{pin}/dist/katex.min.js",
        "katex.min.css": "https://cdn.jsdelivr.net/npm/katex@{pin}/dist/katex.min.css",
    },
    "iconify": {
        "iconify/fa.json": "https://unpkg.com/@iconify-json/fa@{pin}/icons.json",
        "iconify/mdi.json": "https://unpkg.com/@iconify-json/mdi@{pin}/icons.json",
        "iconify/logos.json": "https://unpkg.com/@iconify-json/logos@{pin}/icons.json",
    },
}


@dataclass
class VendorProvisionResult:
    downloaded: list[str]
    skipped: list[str]
    errors: list[str]
    integrity: dict[str, str] = field(default_factory=dict)


class CapabilityVendorHelper:
    """Download or copy vendor files for enabled capabilities."""

    def __init__(self, config: Mapping[str, Any], site_root: Path):
        self.config = config
        self.site_root = site_root
        self.vendor_dir = vendor_dir_for_site(site_root)
        self.integrity: dict[str, str] = {}

    def process(self) -> VendorProvisionResult:
        downloaded: list[str] = []
        skipped: list[str] = []
        errors: list[str] = []

        for name, sources in VENDOR_SOURCES.items():
            if not is_capability_requested(self.config, name):
                continue
            for rel_path, default_url in sources.items():
                dest = self.vendor_dir / rel_path
                if dest.is_file() and dest.stat().st_size > 0:
                    try:
                        data = dest.read_bytes()
                        record_vendor_integrity(
                            self.integrity,
                            rel_path,
                            data,
                            require_sri=False,
                        )
                        skipped.append(rel_path)
                    except Exception as exc:
                        errors.append(f"{rel_path}: {exc}")
                    continue
                try:
                    resolved = resolve_vendor_asset(
                        self.config,
                        name,
                        rel_path,
                        default_url,
                        site_root=self.site_root,
                    )
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if resolved.source_mode == "local":
                        if resolved.local_path is None or not resolved.local_path.is_file():
                            msg = f"local source missing: {resolved.local_path}"
                            raise FileNotFoundError(msg)
                        data = resolved.local_path.read_bytes()
                    else:
                        raw = urlopen_with_ssl_fallback(
                            resolved.url or default_url,
                            timeout=30,
                            user_agent=_VENDOR_USER_AGENT,
                            decode=False,
                        )
                        data = raw if isinstance(raw, bytes) else raw.encode("utf-8")

                    record_vendor_integrity(
                        self.integrity,
                        rel_path,
                        data,
                        expected_sri=resolved.expected_sri,
                        require_sri=resolved.require_sri,
                    )
                    atomic_write_bytes(dest, data)
                    downloaded.append(rel_path)
                    logger.info(
                        "capability_vendor_provisioned",
                        file=rel_path,
                        capability=name,
                        source=resolved.source_mode,
                    )
                except Exception as exc:
                    msg = f"{rel_path}: {exc}"
                    errors.append(msg)
                    logger.warning(
                        "capability_vendor_provision_failed",
                        file=rel_path,
                        error=str(exc),
                    )

        self._write_integrity_manifest()
        return VendorProvisionResult(
            downloaded=downloaded,
            skipped=skipped,
            errors=errors,
            integrity=dict(self.integrity),
        )

    def _write_integrity_manifest(self) -> None:
        if not self.integrity:
            return
        manifest_path = self.vendor_dir / _INTEGRITY_MANIFEST
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(
            manifest_path,
            json.dumps(self.integrity, indent=2, sort_keys=True).encode("utf-8"),
        )


def load_vendor_integrity(vendor_dir: Path) -> dict[str, str]:
    """Load SRI hashes written during vendor provisioning."""
    manifest_path = vendor_dir / _INTEGRITY_MANIFEST
    if not manifest_path.is_file():
        return {}
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def vendor_integrity_for_path(vendor_dir: Path, rel_path: str) -> str | None:
    """Return integrity attribute for a vendor relative path, if known."""
    return load_vendor_integrity(vendor_dir).get(rel_path)


def required_vendor_paths(config: Mapping[str, Any]) -> list[str]:
    """Relative paths under assets/vendor/ for all requested capabilities."""
    paths: list[str] = []
    for name in VENDOR_SOURCES:
        if is_capability_requested(config, name):
            paths.extend(VENDOR_FILES.get(name, ()))
    return paths
