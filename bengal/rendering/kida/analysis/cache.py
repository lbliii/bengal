"""Cache scope inference for template blocks.

Determines recommended caching granularity based on dependencies and purity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from bengal.rendering.kida.analysis.config import AnalysisConfig

CacheScope = Literal["none", "page", "site", "unknown"]


def infer_cache_scope(
    depends_on: frozenset[str],
    is_pure: Literal["pure", "impure", "unknown"],
    config: AnalysisConfig | None = None,
) -> CacheScope:
    """Infer recommended cache scope for a block.

    Args:
        depends_on: Context paths the block depends on.
        is_pure: Block purity level.
        config: Analysis configuration (for naming conventions).

    Returns:
        Recommended cache scope:
        - "site": Can cache once per site build (no page-specific deps)
        - "page": Must re-render per page, but cacheable
        - "none": Cannot be cached (impure)
        - "unknown": Cannot determine

    Example:
        >>> infer_cache_scope(frozenset({"site.pages"}), "pure")
        'site'

        >>> infer_cache_scope(frozenset({"page.title"}), "pure")
        'page'

        >>> infer_cache_scope(frozenset({"items"}), "impure")
        'none'
    """
    # Use default config if not provided
    if config is None:
        from bengal.rendering.kida.analysis.config import DEFAULT_CONFIG

        config = DEFAULT_CONFIG

    # Impure blocks cannot be cached
    if is_pure == "impure":
        return "none"

    # Unknown purity means unknown cacheability
    if is_pure == "unknown":
        return "unknown"

    # Pure block - check dependencies
    if not depends_on:
        # No dependencies - can cache forever (site-wide)
        return "site"

    # Check if any dependency is page-specific
    has_page_dep = _has_prefix_match(depends_on, config.page_prefixes)

    if has_page_dep:
        # Depends on page - must cache per-page
        return "page"

    # Only site-level dependencies - can cache site-wide
    return "site"


def _has_prefix_match(paths: frozenset[str], prefixes: frozenset[str]) -> bool:
    """Check if any path starts with any prefix.

    Handles both "page." (prefix) and "page" (exact match) patterns.
    """
    for path in paths:
        for prefix in prefixes:
            # Handle exact match (prefix without dot)
            if prefix == path:
                return True
            # Handle prefix match (prefix with dot)
            if prefix.endswith(".") and path.startswith(prefix):
                return True
            # Handle prefix that should be dotted
            if not prefix.endswith(".") and (path == prefix or path.startswith(prefix + ".")):
                return True
    return False
