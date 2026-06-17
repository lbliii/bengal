"""
Build-time vendor provisioning for opt-in diagram/math capabilities.

Downloads pinned vendor assets into ``assets/vendor/`` when a capability is
enabled in config. Network I/O happens at build time only — runtime output
uses self-hosted same-origin URLs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bengal import __version__ as BENGAL_VERSION
from bengal.capabilities.runtime import (
    VENDOR_FILES,
    is_capability_requested,
    vendor_dir_for_site,
)
from bengal.fonts.utils import urlopen_with_ssl_fallback
from bengal.utils.io.atomic_write import atomic_write_bytes
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

logger = get_logger(__name__)

_VENDOR_USER_AGENT = f"Bengal/{BENGAL_VERSION} (capability-vendor-provisioning)"

# Pinned upstream URLs — fetched at build time only, never referenced in HTML output.
VENDOR_SOURCES: dict[str, dict[str, str]] = {
    "mermaid": {
        "mermaid.min.js": "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js",
    },
    "katex": {
        "katex.min.js": "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js",
        "katex.min.css": "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css",
    },
    "iconify": {
        "iconify/fa.json": "https://unpkg.com/@iconify-json/fa@1/icons.json",
        "iconify/mdi.json": "https://unpkg.com/@iconify-json/mdi@1/icons.json",
        "iconify/logos.json": "https://unpkg.com/@iconify-json/logos@1/icons.json",
    },
}


@dataclass
class VendorProvisionResult:
    downloaded: list[str]
    skipped: list[str]
    errors: list[str]


class CapabilityVendorHelper:
    """Download missing vendor files for enabled capabilities."""

    def __init__(self, config: Mapping[str, Any], site_root: Path):
        self.config = config
        self.vendor_dir = vendor_dir_for_site(site_root)

    def process(self) -> VendorProvisionResult:
        downloaded: list[str] = []
        skipped: list[str] = []
        errors: list[str] = []

        for name, sources in VENDOR_SOURCES.items():
            if not is_capability_requested(self.config, name):
                continue
            for rel_path, url in sources.items():
                dest = self.vendor_dir / rel_path
                if dest.is_file() and dest.stat().st_size > 0:
                    skipped.append(rel_path)
                    continue
                try:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    data = urlopen_with_ssl_fallback(
                        url,
                        timeout=30,
                        user_agent=_VENDOR_USER_AGENT,
                        decode=False,
                    )
                    if not isinstance(data, bytes):
                        data = data.encode("utf-8")
                    atomic_write_bytes(dest, data)
                    downloaded.append(rel_path)
                    logger.info("capability_vendor_downloaded", file=rel_path, capability=name)
                except Exception as exc:
                    msg = f"{rel_path}: {exc}"
                    errors.append(msg)
                    logger.warning(
                        "capability_vendor_download_failed", file=rel_path, error=str(exc)
                    )

        return VendorProvisionResult(downloaded=downloaded, skipped=skipped, errors=errors)


def required_vendor_paths(config: Mapping[str, Any]) -> list[str]:
    """Relative paths under assets/vendor/ for all requested capabilities."""
    paths: list[str] = []
    for name in VENDOR_SOURCES:
        if is_capability_requested(config, name):
            paths.extend(VENDOR_FILES.get(name, ()))
    return paths
