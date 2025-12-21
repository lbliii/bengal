"""
Constants for incremental build logic.

Shared between bengal.server.build_handler and bengal.orchestration.incremental.

RFC: rfc-incremental-hot-reload-invariants
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
