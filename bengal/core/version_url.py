"""Version URL computation for cross-version navigation.

Pure logic for computing version-aware URLs with smart fallback.
Used by Site.get_version_target_url and rendering template registration.
No rendering imports.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from bengal.core.utils.url import apply_baseurl, get_baseurl

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SiteLike


def _apply_baseurl(path: str, site: SiteLike) -> str:
    """Apply baseurl from site to path."""
    return apply_baseurl(path, get_baseurl(site))


def get_version_target_url(
    page: PageLike | None, target_version: dict[str, Any] | None, site: SiteLike
) -> str:
    """
    Compute the best URL for navigating to a page in the target version.

    Implements a fallback cascade:
    1. If exact equivalent page exists → return that URL
    2. If section index exists → return section index URL
    3. Otherwise → return version root URL

    All returned URLs include baseurl for proper template use.
    """
    if not page or not target_version:
        return _apply_baseurl("/", site)

    if not site.versioning_enabled:
        site_path = getattr(page, "_path", None) or "/"
        return _apply_baseurl(site_path, site)

    target_version_id = target_version.get("id", "")
    target_is_latest = target_version.get("latest", False)
    current_version_id = getattr(page, "version", None)

    if current_version_id == target_version_id:
        site_path = getattr(page, "_path", None) or "/"
        return _apply_baseurl(site_path, site)

    current_url = getattr(page, "_path", None) or "/"
    target_url = _construct_version_url(
        current_url, current_version_id, target_version_id, target_is_latest, site
    )

    if page_exists_in_version(target_url, target_version_id, site):
        return _apply_baseurl(target_url, site)

    path_parts = target_url.rstrip("/").split("/")
    for i in range(len(path_parts) - 1, 0, -1):
        parent_url = "/".join(path_parts[:i]) + "/"
        if parent_url == "/":
            break
        if page_exists_in_version(parent_url, target_version_id, site):
            return _apply_baseurl(parent_url, site)

    section_index_url = _get_section_index_url(target_url)
    if section_index_url and page_exists_in_version(section_index_url, target_version_id, site):
        return _apply_baseurl(section_index_url, site)

    version_root = _get_version_root_url(target_version_id, target_is_latest, site)
    return _apply_baseurl(version_root, site)


def _construct_version_url(
    current_url: str,
    current_version_id: str | None,
    target_version_id: str,
    target_is_latest: bool,
    site: SiteLike,
) -> str:
    """Construct the equivalent URL in the target version."""
    sections = site.version_config.sections if site.version_config else ["docs"]

    current_prefix = ""
    if current_version_id:
        current_version = site.version_config.get_version(current_version_id)
        if current_version and not current_version.latest:
            current_prefix = f"/{current_version_id}"

    target_prefix = "" if target_is_latest else f"/{target_version_id}"

    for section in sections:
        section_prefix = f"/{section}"

        if current_prefix:
            versioned_section = f"{section_prefix}{current_prefix}/"
            if current_url.startswith(versioned_section):
                rest = current_url[len(versioned_section) :]
                if target_is_latest:
                    return f"{section_prefix}/{rest}"
                return f"{section_prefix}{target_prefix}/{rest}"
        else:
            if current_url.startswith(f"{section_prefix}/"):
                rest = current_url[len(section_prefix) + 1 :]
                if target_is_latest:
                    return current_url
                return f"{section_prefix}{target_prefix}/{rest}"

    return current_url


def _get_section_index_url(url: str) -> str | None:
    """Get the parent section index URL."""
    if not url or url == "/":
        return None
    url = url.rstrip("/")
    parts = url.split("/")
    if len(parts) <= 2:
        return None
    return "/".join(parts[:-1]) + "/"


def _get_version_root_url(version_id: str, is_latest: bool, site: SiteLike) -> str:
    """Get the root URL for a version."""
    sections = site.version_config.sections if site.version_config else ["docs"]
    section = sections[0] if sections else "docs"
    if is_latest:
        return f"/{section}/"
    return f"/{section}/{version_id}/"


_version_page_index_cache: dict[int, dict[str, set[str]]] = {}
_version_cache_lock = threading.Lock()
_VERSION_INDEX_CACHE_MAX_SIZE = 10


def _build_version_page_index(site: SiteLike) -> dict[str, set[str]]:
    """Build an index of page URLs by version for O(1) existence checks."""
    site_id = id(site)
    with _version_cache_lock:
        if site_id in _version_page_index_cache:
            return _version_page_index_cache[site_id]

        if len(_version_page_index_cache) >= _VERSION_INDEX_CACHE_MAX_SIZE:
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
            if url.endswith("/") and len(url) > 1:
                index[version].add(url.rstrip("/"))

    with _version_cache_lock:
        _version_page_index_cache[site_id] = index
    return index


def page_exists_in_version(path: str, version_id: str, site: SiteLike) -> bool:
    """Check if a page exists in a specific version."""
    if not site.versioning_enabled:
        return False

    index = _build_version_page_index(site)
    version_pages = index.get(version_id, set())

    normalized = path.rstrip("/") if path != "/" else path
    with_slash = path if path.endswith("/") else path + "/"

    return normalized in version_pages or with_slash in version_pages


def invalidate_version_page_index() -> None:
    """Invalidate the cached version page index."""
    with _version_cache_lock:
        _version_page_index_cache.clear()


try:
    from bengal.utils.cache_registry import InvalidationReason, register_cache

    register_cache(
        "version_page_index",
        invalidate_version_page_index,
        invalidate_on={
            InvalidationReason.CONFIG_CHANGED,
            InvalidationReason.STRUCTURAL_CHANGE,
            InvalidationReason.FULL_REBUILD,
            InvalidationReason.TEST_CLEANUP,
        },
        depends_on={"nav_tree"},
    )
except ImportError:
    pass
