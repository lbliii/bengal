"""
Declarative capability specifications (#572).

Each capability bundles provisioning, content detection, and (optionally)
render/init contracts. Third-party packages register specs via the
``bengal.capabilities`` entry-point group.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

LoadPosition = Literal["head", "body"]


@dataclass(frozen=True, slots=True)
class CapabilityAsset:
    """One vendor file provisioned at build time."""

    rel_path: str
    url_template: str


@dataclass(frozen=True, slots=True)
class CapabilityInitContract:
    """Declarative JS runtime init contract (theme wiring is separate)."""

    load_position: LoadPosition = "body"
    defer: bool = True
    module: bool = False
    lazy_loader_key: str | None = None


@dataclass(frozen=True, slots=True)
class CapabilitySpec:
    """
    Author-owned declaration for an opt-in runtime capability.

    Site owners enable capabilities in ``[capabilities]``; content detectors
    decide per-page emission (#571).
    """

    name: str
    default_pin: str
    assets: tuple[CapabilityAsset, ...]
    html_patterns: tuple[str, ...] = ()
    source_patterns: tuple[str, ...] = ()
    metadata_keys: tuple[str, ...] = ()
    fence_languages: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    implies: tuple[str, ...] = ()
    init: CapabilityInitContract | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            msg = "CapabilitySpec.name must be a non-empty string"
            raise ValueError(msg)
        if not self.assets:
            msg = f"CapabilitySpec {self.name!r} must declare at least one asset"
            raise ValueError(msg)

    def has_content_detector(self) -> bool:
        return bool(self.html_patterns or self.source_patterns or self.metadata_keys)

    @property
    def vendor_files(self) -> tuple[str, ...]:
        return tuple(asset.rel_path for asset in self.assets)

    @property
    def vendor_urls(self) -> dict[str, str]:
        return {asset.rel_path: asset.url_template for asset in self.assets}

    def compiled_html_patterns(self) -> tuple[re.Pattern[str], ...]:
        return tuple(re.compile(p, re.IGNORECASE) for p in self.html_patterns)

    def compiled_source_patterns(self) -> tuple[re.Pattern[str], ...]:
        return tuple(re.compile(p, re.IGNORECASE) for p in self.source_patterns)
