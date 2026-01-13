"""
Centralized asset URL resolution for all template engines.

This module provides a single source of truth for resolving asset URLs,
handling fingerprinting, baseurl, and file:// protocol. Template engine
adapters should use this instead of implementing their own logic.

Usage in adapters:
    from bengal.rendering.assets import resolve_asset_url

    def asset_url(path: str) -> str:
        return resolve_asset_url(path, site, page)

Benefits:
- Single implementation to maintain
- All engines get fingerprinting support automatically
- Third-party engines don't need to understand manifest internals
- Easier to add new features (CDN, versioning, etc.)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


def resolve_asset_url(
    asset_path: str,
    site: Site,
    page: Any = None,
) -> str:
    """
    Resolve an asset path to its final URL.
    
    This is the single source of truth for asset URL resolution.
    Handles fingerprinting, baseurl, and file:// protocol.
    
    Args:
        asset_path: Logical asset path (e.g., 'css/style.css')
        site: Site instance
        page: Optional page context (for file:// relative paths)
    
    Returns:
        Resolved asset URL ready for use in HTML
    
    Example:
            >>> resolve_asset_url('css/style.css', site)
            '/bengal/assets/css/style.abc123.css'  # Fingerprinted
            >>> resolve_asset_url('css/style.css', site)  # Dev mode
            '/bengal/assets/css/style.css'  # Non-fingerprinted
        
    """
    from bengal.rendering.template_engine.url_helpers import with_baseurl

    if not asset_path:
        return with_baseurl("/assets/", site)

    # Normalize path
    clean_path = asset_path.replace("\\", "/").strip().lstrip("/")

    baseurl_value = (site.baseurl or "").rstrip("/")

    # Handle file:// protocol - generate relative URLs
    if baseurl_value.startswith("file://"):
        return _resolve_file_protocol(clean_path, site, page)

    # In dev server mode, prefer stable URLs without fingerprints
    if getattr(site, "dev_mode", False):
        return with_baseurl(f"/assets/{clean_path}", site)

    # Look up fingerprinted path from manifest
    fingerprinted_path = _resolve_fingerprinted(clean_path, site)
    if fingerprinted_path:
        return with_baseurl(f"/{fingerprinted_path}", site)

    # Fallback: return direct asset path
    return with_baseurl(f"/assets/{clean_path}", site)


def _resolve_fingerprinted(logical_path: str, site: Site) -> str | None:
    """
    Resolve a logical asset path to its fingerprinted output path.
    
    Uses a cached manifest for efficient lookups across all template renders.
    
    Args:
        logical_path: Logical asset path (e.g., 'css/style.css')
        site: Site instance
    
    Returns:
        Fingerprinted output path (e.g., 'assets/css/style.abc123.css') or None
        
    """
    from bengal.assets.manifest import AssetManifest

    # Use a single cache on the site for all engines
    cache_attr = "_asset_manifest_cache"
    manifest_cache = getattr(site, cache_attr, None)

    if manifest_cache is None:
        # Load manifest from output directory
        manifest_path = site.output_dir / "asset-manifest.json"
        manifest = AssetManifest.load(manifest_path)
        if manifest is None:
            # No manifest available - cache empty dict to avoid repeated loads
            setattr(site, cache_attr, {})
            return None
        # Cache the entries dict for fast lookups
        manifest_cache = dict(manifest.entries)
        setattr(site, cache_attr, manifest_cache)

    entry = manifest_cache.get(logical_path)
    if entry:
        return entry.output_path
    return None


def _resolve_file_protocol(asset_path: str, site: Site, page: Any = None) -> str:
    """
    Generate asset URL for file:// protocol using relative paths.
    
    Args:
        asset_path: Validated asset path
        site: Site instance
        page: Page context for computing relative path
    
    Returns:
        Relative asset URL
        
    """
    asset_url_path = f"assets/{asset_path}"

    # Try to compute relative path from page
    if page and hasattr(page, "output_path") and page.output_path:
        try:
            page_rel_to_root = page.output_path.relative_to(site.output_dir)
            depth = (
                len(page_rel_to_root.parent.parts) if page_rel_to_root.parent != Path(".") else 0
            )
            if depth > 0:
                relative_prefix = "/".join([".."] * depth)
                return f"{relative_prefix}/{asset_url_path}"
            else:
                return f"./{asset_url_path}"
        except (ValueError, AttributeError):
            pass

    # Fallback: assume root-level
    return f"./{asset_url_path}"


def clear_manifest_cache(site: Site) -> None:
    """
    Clear the asset manifest cache on the site.
    
    Call this when the manifest has been updated (e.g., after asset processing).
    
    Args:
        site: Site instance
        
    """
    cache_attr = "_asset_manifest_cache"
    if hasattr(site, cache_attr):
        delattr(site, cache_attr)
