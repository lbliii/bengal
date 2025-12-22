"""
URL Ownership Policy Configuration.

This module defines reserved URL namespaces and ownership rules for URL
coordination within Bengal sites. It's used by the URL registry and validation
systems to prevent URL conflicts between user content and system-generated pages.

Reserved Namespaces:
    - ``/tags/``: Taxonomy pages (owned by taxonomy system)
    - ``/search/``: Search page (owned by special_pages)
    - ``/404/``: Error page (owned by special_pages)
    - ``/graph/``: Graph visualization (owned by special_pages)
    - Additional namespaces can be configured dynamically via autodoc settings

Module Attributes:
    RESERVED_NAMESPACES: Base mapping of namespace prefixes to ownership metadata.

Key Functions:
    get_reserved_namespaces: Get all reserved namespaces including dynamic autodoc prefixes.
    is_reserved_namespace: Check if a URL falls within a reserved namespace.

Example:
    >>> is_reserved_namespace("/tags/python/")
    (True, 'taxonomy')
    >>> is_reserved_namespace("/blog/my-post/")
    (False, None)

See Also:
    - URL registry in :mod:`bengal.core.url_registry`: Uses policy for conflict detection.
    - Health validators: Check for namespace violations.
"""

from __future__ import annotations

from typing import Any

# Reserved namespace patterns based on existing generators
# Format: {namespace_prefix: {owner: str, priority: int}}
# - owner: Who "owns" this namespace (for diagnostics)
# - priority: Default priority for claims in this namespace
RESERVED_NAMESPACES: dict[str, dict[str, Any]] = {
    "tags": {"owner": "taxonomy", "priority": 40},
    "search": {"owner": "special_pages", "priority": 10},
    "404": {"owner": "special_pages", "priority": 10},
    "graph": {"owner": "special_pages", "priority": 10},
    # Autodoc prefixes are configured at runtime from site config
    # They are added dynamically based on autodoc.output_prefix values
}


def get_reserved_namespaces(site_config: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """
    Get all reserved namespaces including dynamically configured prefixes.

    Returns the base reserved namespaces plus any additional namespaces
    configured through autodoc settings in the site configuration.

    Args:
        site_config: Site configuration dictionary. If provided, autodoc
            prefixes are extracted and added to the reserved namespaces.

    Returns:
        Dictionary mapping namespace prefixes to ownership metadata.
        Each entry contains ``"owner"`` (string) and ``"priority"`` (int).

    Example:
        >>> namespaces = get_reserved_namespaces()
        >>> namespaces["tags"]
        {'owner': 'taxonomy', 'priority': 40}

        >>> # With autodoc configuration
        >>> config = {"autodoc": {"python": {"enabled": True, "output_prefix": "api/python"}}}
        >>> namespaces = get_reserved_namespaces(config)
        >>> "api" in namespaces
        True
    """
    namespaces = dict(RESERVED_NAMESPACES)

    # Add autodoc prefixes from config if available
    if site_config:
        autodoc_config = site_config.get("autodoc", {})
        if isinstance(autodoc_config, dict):
            # Check each autodoc type for output_prefix
            for autodoc_type in ["python", "openapi", "cli"]:
                type_config = autodoc_config.get(autodoc_type, {})
                if isinstance(type_config, dict) and type_config.get("enabled"):
                    prefix = type_config.get("output_prefix", "")
                    if prefix:
                        # Extract first segment as namespace (e.g., "api/python" -> "api")
                        first_segment = prefix.split("/")[0]
                        if first_segment and first_segment not in namespaces:
                            namespaces[first_segment] = {
                                "owner": f"autodoc:{autodoc_type}",
                                "priority": 90 if autodoc_type == "python" else 80,
                            }

    return namespaces


def is_reserved_namespace(
    url: str, site_config: dict[str, Any] | None = None
) -> tuple[bool, str | None]:
    """
    Check if a URL falls within a reserved namespace.

    Examines the first path segment of the URL to determine if it matches
    any reserved namespace prefix.

    Args:
        url: URL to check (e.g., ``"/tags/python/"``, ``"/search/"``).
            Leading and trailing slashes are normalized.
        site_config: Site configuration dictionary. If provided, includes
            dynamically configured autodoc namespaces in the check.

    Returns:
        Tuple of ``(is_reserved, owner_name)``:
            - ``is_reserved``: ``True`` if the URL is in a reserved namespace.
            - ``owner_name``: The owner identifier (e.g., ``"taxonomy"``),
              or ``None`` if not reserved.

    Example:
        >>> is_reserved_namespace("/tags/python/")
        (True, 'taxonomy')
        >>> is_reserved_namespace("/blog/my-post/")
        (False, None)
        >>> is_reserved_namespace("/search/")
        (True, 'special_pages')
    """
    # Normalize URL: remove leading/trailing slashes, get first segment
    url = url.strip("/")
    if not url:
        return False, None

    first_segment = url.split("/")[0]
    namespaces = get_reserved_namespaces(site_config)

    # Check exact match or prefix match
    for namespace, metadata in namespaces.items():
        if first_segment == namespace or url.startswith(f"{namespace}/"):
            return True, metadata.get("owner", "unknown")

    return False, None
