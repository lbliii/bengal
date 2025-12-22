"""
Version URL functions for templates.

Provides functions for computing version-aware URLs with smart fallback
for cross-version navigation. Enables the version selector to always land
on valid pages instead of 404 errors.

Key function:
    get_version_target_url(page, version, site) -> URL to navigate to when switching versions

Design:
    Pre-computes fallback URLs at build time for instant client-side navigation.
    No runtime manifest fetch or HEAD requests needed.

Engine-Agnostic Access:
    The preferred way to use this is via the Site method:

        site.get_version_target_url(page, version)

    This works with any template engine (Jinja2, Mako, BYORenderer).
    The Jinja2 global function is also available.

    Example (Jinja2):
        {{ site.get_version_target_url(page, v) }}

    Example (Mako):
        ${site.get_version_target_url(page, v)}
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.rendering.template_engine.url_helpers import with_baseurl
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from jinja2 import Environment

    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


def register(env: Environment, site: Site) -> None:
    """
    Register version URL functions with Jinja2 environment.

    Registers global functions for template use: {{ get_version_target_url(page, v) }}

    The preferred engine-agnostic approach is to use the Site method:
        {{ site.get_version_target_url(page, v) }}

    This Site method works with any template engine, not just Jinja2.
    """

    def get_version_target_url_wrapper(
        page: Page | None, target_version: dict[str, Any] | None
    ) -> str:
        """
        Get the best URL for a page in the target version.

        Computes the fallback cascade at build time:
        1. Exact page exists in target version → use it
        2. Section index exists → use section index
        3. Version root → use version root

        Args:
            page: Current page object
            target_version: Target version dict (from site.versions)

        Returns:
            URL to navigate to (always valid, never 404)

        Example:
            {% for v in versions %}
            <option data-target="{{ get_version_target_url(page, v) }}">
              {{ v.label }}
            </option>
            {% endfor %}
        """
        return get_version_target_url(page, target_version, site)

    def page_exists_in_version_wrapper(path: str, version_id: str) -> bool:
        """
        Check if a page exists in a specific version.

        Args:
            path: Page path (e.g., '/docs/guide/')
            version_id: Version ID (e.g., 'v1', 'v2')

        Returns:
            True if page exists in that version
        """
        return page_exists_in_version(path, version_id, site)

    env.globals.update(
        {
            "get_version_target_url": get_version_target_url_wrapper,
            "page_exists_in_version": page_exists_in_version_wrapper,
        }
    )


def get_version_target_url(
    page: Page | None, target_version: dict[str, Any] | None, site: Site
) -> str:
    """
    Compute the best URL for navigating to a page in the target version.

    Implements a fallback cascade:
    1. If exact equivalent page exists → return that URL
    2. If section index exists → return section index URL
    3. Otherwise → return version root URL

    All returned URLs include baseurl (using href logic) for proper template use.

    Args:
        page: Current page (may be None for edge cases)
        target_version: Target version dict with 'id', 'url_prefix', 'latest' keys
        site: Site instance

    Returns:
        Best URL to navigate to (guaranteed to exist, includes baseurl)
    """
    # Edge cases: return root if we don't have valid inputs
    if not page or not target_version:
        return with_baseurl("/", site)

    if not site.versioning_enabled:
        # Versioning not enabled, return current page URL with baseurl
        site_path = getattr(page, "_path", None) or "/"
        return with_baseurl(site_path, site)

    target_version_id = target_version.get("id", "")
    target_is_latest = target_version.get("latest", False)
    current_version_id = getattr(page, "version", None)

    # Same version - no change needed, but still apply baseurl
    if current_version_id == target_version_id:
        site_path = getattr(page, "_path", None) or "/"
        return with_baseurl(site_path, site)

    # Get the current page URL
    current_url = getattr(page, "_path", None) or "/"

    # Construct the equivalent URL in the target version
    target_url = _construct_version_url(
        current_url, current_version_id, target_version_id, target_is_latest, site
    )

    # Check if the target page exists
    if page_exists_in_version(target_url, target_version_id, site):
        return with_baseurl(target_url, site)

    # Fallback 1: Try parent directories progressively (preserve location better)
    # This helps retain user's position in the hierarchy
    path_parts = target_url.rstrip("/").split("/")
    for i in range(len(path_parts) - 1, 0, -1):
        parent_url = "/".join(path_parts[:i]) + "/"
        if parent_url == "/":
            break
        if page_exists_in_version(parent_url, target_version_id, site):
            return with_baseurl(parent_url, site)

    # Fallback 2: Try section index (original fallback)
    section_index_url = _get_section_index_url(target_url)
    if section_index_url and page_exists_in_version(section_index_url, target_version_id, site):
        return with_baseurl(section_index_url, site)

    # Fallback 3: Version root
    version_root = _get_version_root_url(target_version_id, target_is_latest, site)
    return with_baseurl(version_root, site)


def _construct_version_url(
    current_url: str,
    current_version_id: str | None,
    target_version_id: str,
    target_is_latest: bool,
    site: Site,
) -> str:
    """
    Construct the equivalent URL in the target version.

    URL transformations:
    - /docs/guide/ (latest) → /docs/v1/guide/ (older)
    - /docs/v1/guide/ (older) → /docs/guide/ (latest)
    - /docs/v1/guide/ (older) → /docs/v2/guide/ (other older)
    """
    sections = site.version_config.sections if site.version_config else ["docs"]

    # Determine current version prefix (empty for latest)
    current_prefix = ""
    if current_version_id:
        current_version = site.version_config.get_version(current_version_id)
        if current_version and not current_version.latest:
            current_prefix = f"/{current_version_id}"

    # Determine target version prefix (empty for latest)
    target_prefix = "" if target_is_latest else f"/{target_version_id}"

    # Find which section this URL belongs to
    for section in sections:
        section_prefix = f"/{section}"

        # Check if URL is in this versioned section
        if current_prefix:
            # Current is older version: /docs/v1/guide/
            versioned_section = f"{section_prefix}{current_prefix}/"
            if current_url.startswith(versioned_section):
                # Extract the path after version prefix
                rest = current_url[len(versioned_section) :]
                if target_is_latest:
                    # Going to latest: /docs/guide/
                    return f"{section_prefix}/{rest}"
                else:
                    # Going to another older version: /docs/v2/guide/
                    return f"{section_prefix}{target_prefix}/{rest}"
        else:
            # Current is latest: /docs/guide/
            if current_url.startswith(f"{section_prefix}/"):
                rest = current_url[len(section_prefix) + 1 :]
                if target_is_latest:
                    # Already latest
                    return current_url
                else:
                    # Going to older version: /docs/v1/guide/
                    return f"{section_prefix}{target_prefix}/{rest}"

    # URL not in a versioned section, return as-is
    return current_url


def _get_section_index_url(url: str) -> str | None:
    """
    Get the parent section index URL.

    /docs/v1/guide/advanced/ → /docs/v1/guide/
    /docs/guide/advanced/ → /docs/guide/
    /docs/v1/ → None (already at root)
    """
    if not url or url == "/":
        return None

    # Remove trailing slash and get parent
    url = url.rstrip("/")
    parts = url.split("/")

    if len(parts) <= 2:
        # Already at version root level
        return None

    # Remove last segment
    parent_url = "/".join(parts[:-1]) + "/"
    return parent_url


def _get_version_root_url(version_id: str, is_latest: bool, site: Site) -> str:
    """
    Get the root URL for a version.

    For latest: /docs/
    For older: /docs/v1/
    """
    sections = site.version_config.sections if site.version_config else ["docs"]

    # Use first versioned section as the root
    section = sections[0] if sections else "docs"

    if is_latest:
        return f"/{section}/"
    else:
        return f"/{section}/{version_id}/"


# Module-level cache for version page index (keyed by id(site))
# Limited to 10 entries to prevent memory leaks when Site objects are recreated
_version_page_index_cache: dict[int, dict[str, set[str]]] = {}
_VERSION_INDEX_CACHE_MAX_SIZE = 10


def _build_version_page_index(site: Site) -> dict[str, set[str]]:
    """
    Build an index of page URLs by version for O(1) existence checks.

    Uses a module-level cache keyed by site id to avoid rebuilding
    the index on every call. Cache is invalidated via invalidate_version_page_index().

    Memory leak prevention: Cache is limited to 10 entries. When limit is reached,
    oldest entries are evicted (FIFO). This prevents unbounded growth when Site
    objects are recreated frequently (e.g., in dev server).

    Returns:
        Dict mapping version_id to set of relative URLs
    """
    site_id = id(site)
    if site_id in _version_page_index_cache:
        return _version_page_index_cache[site_id]

    # Evict oldest entry if cache is full (prevent memory leak)
    if len(_version_page_index_cache) >= _VERSION_INDEX_CACHE_MAX_SIZE:
        # Remove first (oldest) entry
        oldest_key = next(iter(_version_page_index_cache))
        _version_page_index_cache.pop(oldest_key, None)

    index: dict[str, set[str]] = {}

    for page in site.pages:
        version = getattr(page, "version", None)
        if version is None:
            continue

        if version not in index:
            index[version] = set()

        url = getattr(page, "_path", None)
        if url:
            index[version].add(url)
            # Also add without trailing slash for flexibility
            if url.endswith("/") and len(url) > 1:
                index[version].add(url.rstrip("/"))

    _version_page_index_cache[site_id] = index
    return index


def page_exists_in_version(path: str, version_id: str, site: Site) -> bool:
    """
    Check if a page exists in a specific version.

    Uses cached index for O(1) lookup.

    Args:
        path: Page path (e.g., '/docs/guide/' or '/docs/v1/guide/')
        version_id: Version ID to check
        site: Site instance

    Returns:
        True if page exists in that version
    """
    if not site.versioning_enabled:
        return False

    # Build or get cached index
    # Note: We use id(site.pages) as a cache key indicator
    # The cache is invalidated when pages list changes
    index = _build_version_page_index(site)

    version_pages = index.get(version_id, set())

    # Normalize path
    normalized = path.rstrip("/") if path != "/" else path
    with_slash = path if path.endswith("/") else path + "/"

    return normalized in version_pages or with_slash in version_pages


def invalidate_version_page_index() -> None:
    """
    Invalidate the cached version page index.

    Call this when pages are modified during a build.
    """
    _version_page_index_cache.clear()
