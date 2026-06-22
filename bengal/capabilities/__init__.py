"""Opt-in runtime capabilities (Mermaid, KaTeX, Iconify)."""

from bengal.capabilities.detectors import (
    detect_capabilities_in_html,
    detect_capabilities_in_source,
    detect_page_capabilities_needed,
    resolve_effective_capabilities,
)
from bengal.capabilities.runtime import (
    CAPABILITY_NAMES,
    resolve_runtime_capabilities,
    vendor_dir_for_site,
    vendors_present,
)
from bengal.capabilities.vendors import (
    CapabilityVendorHelper,
    VendorProvisionResult,
    load_vendor_integrity,
    vendor_integrity_for_path,
)

__all__ = [
    "CAPABILITY_NAMES",
    "CapabilityVendorHelper",
    "VendorProvisionResult",
    "detect_capabilities_in_html",
    "detect_capabilities_in_source",
    "detect_page_capabilities_needed",
    "load_vendor_integrity",
    "resolve_effective_capabilities",
    "resolve_runtime_capabilities",
    "vendor_dir_for_site",
    "vendor_integrity_for_path",
    "vendors_present",
]
