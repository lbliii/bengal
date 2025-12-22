"""
Constants for incremental build logic.

Defines frontmatter keys that affect navigation and require section-wide
rebuilds when changed. Other metadata changes only require page-only rebuilds.

This module provides the NAV_AFFECTING_KEYS constant and helper functions
for extracting navigation-relevant metadata from pages.

Usage:
    from bengal.orchestration.constants import NAV_AFFECTING_KEYS, extract_nav_metadata

    # Check if a key affects navigation
    if 'title' in NAV_AFFECTING_KEYS:
        rebuild_section()

    # Extract only nav-affecting metadata for comparison
    nav_meta = extract_nav_metadata(page.metadata)

Related Modules:
    bengal.server.build_handler: Uses for hot reload decisions
    bengal.orchestration.incremental: Uses for rebuild scope detection

See Also:
    plan/ready/rfc-incremental-hot-reload-invariants.md: Design rationale
"""

from __future__ import annotations

# Frontmatter keys that affect navigation and require section-wide rebuilds when changed.
# Other metadata changes (like tags, description, custom fields) only require page-only rebuilds.
NAV_AFFECTING_KEYS: frozenset[str] = frozenset(
    {
        # Page identity and URL
        "title",
        "slug",
        "permalink",
        "aliases",
        # Visibility (affects section listings and navigation)
        "hidden",
        "draft",
        "visibility",
        # Menu integration
        "menu",
        "weight",
        # Section inheritance (affects all descendant pages)
        "cascade",
        # Redirects
        "redirect",
        # Internationalization
        "lang",
        "language",
        "translationkey",
        # Internal section reference
        "_section",
    }
)


def extract_nav_metadata(metadata: dict) -> dict:
    """
    Extract only nav-affecting keys from metadata.

    Used for comparing whether nav-relevant metadata changed vs body-only changes.

    Args:
        metadata: Full page metadata dict

    Returns:
        Dict containing only nav-affecting keys and their values
    """
    if not metadata:
        return {}
    return {k: v for k, v in metadata.items() if k.lower() in NAV_AFFECTING_KEYS}
