"""Opt-in runtime capabilities (Mermaid, KaTeX, Iconify)."""

from bengal.capabilities.builtins import (
    ICONIFY_CAPABILITY,
    KATEX_CAPABILITY,
    MERMAID_CAPABILITY,
)
from bengal.capabilities.detectors import (
    detect_capabilities_in_html,
    detect_capabilities_in_source,
    detect_page_capabilities_needed,
    resolve_effective_capabilities,
)
from bengal.capabilities.registry import (
    CapabilityRegistry,
    discover_capability_specs,
    get_capability_registry,
    load_capability_registry,
    reset_capability_registry,
)
from bengal.capabilities.runtime import (
    capability_names,
    resolve_runtime_capabilities,
    vendor_dir_for_site,
    vendors_present,
)
from bengal.capabilities.spec import (
    CapabilityAsset,
    CapabilityInitContract,
    CapabilitySpec,
)
from bengal.capabilities.vendors import (
    CapabilityVendorHelper,
    VendorProvisionResult,
    load_vendor_integrity,
    vendor_integrity_for_path,
)

__all__ = [
    "ICONIFY_CAPABILITY",
    "KATEX_CAPABILITY",
    "MERMAID_CAPABILITY",
    "CapabilityAsset",
    "CapabilityInitContract",
    "CapabilityRegistry",
    "CapabilitySpec",
    "CapabilityVendorHelper",
    "VendorProvisionResult",
    "capability_names",
    "detect_capabilities_in_html",
    "detect_capabilities_in_source",
    "detect_page_capabilities_needed",
    "discover_capability_specs",
    "get_capability_registry",
    "load_capability_registry",
    "load_vendor_integrity",
    "reset_capability_registry",
    "resolve_effective_capabilities",
    "resolve_runtime_capabilities",
    "vendor_dir_for_site",
    "vendor_integrity_for_path",
    "vendors_present",
]


# Backward-compatible alias (was a module-level frozenset before #572).
def __getattr__(name: str):
    if name == "CAPABILITY_NAMES":
        return capability_names()
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
