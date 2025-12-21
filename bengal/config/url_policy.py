"""
URL Ownership Policy Configuration.

Defines reserved namespaces and ownership rules for URL coordination.
Used by URLRegistry and OwnershipPolicyValidator to enforce namespace policies.
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
    Get reserved namespaces including runtime-configured autodoc prefixes.

    Args:
        site_config: Site configuration dict (optional, for autodoc prefix detection)

    Returns:
        Dict mapping namespace prefixes to ownership metadata
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

    Args:
        url: URL to check (e.g., "/tags/python/", "/search/")
        site_config: Site configuration dict (optional)

    Returns:
        Tuple of (is_reserved, owner_name) where owner_name is None if not reserved
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


