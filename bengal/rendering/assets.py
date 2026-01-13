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

Thread Safety (Free-Threading / PEP 703):
    Asset manifest access uses ContextVar pattern for thread-local storage.
    Each thread has independent access - no locks needed.
    Set once per build via asset_manifest_context(), read many during render.

RFC: rfc-global-build-state-dependencies.md (Phase 2)
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


# =============================================================================
# Asset Manifest Context (Thread-Safe via ContextVar)
# =============================================================================

__all__ = [
    "AssetManifestContext",
    "get_asset_manifest",
    "set_asset_manifest",
    "reset_asset_manifest",
    "asset_manifest_context",
    "resolve_asset_url",
    "clear_manifest_cache",
]


@dataclass(frozen=True, slots=True)
class AssetManifestContext:
    """Immutable asset manifest context - set once per build, read many.

    Thread Safety:
        ContextVars are thread-local by design (PEP 567).
        Each thread has independent storage - no locks needed.
        Also async-safe (each task gets its own context).

    Attributes:
        entries: Mapping from logical_path to fingerprinted output_path.
        mtime: Manifest file mtime for cache invalidation (optional).
    """

    entries: dict[str, str]  # logical_path -> fingerprinted_output_path
    mtime: float | None = None  # For cache invalidation


# Thread-local manifest via ContextVar (default None for graceful fallback)
_asset_manifest: ContextVar[AssetManifestContext | None] = ContextVar(
    "asset_manifest",
    default=None,
)


def get_asset_manifest() -> AssetManifestContext | None:
    """Get current asset manifest context (thread-local).

    Returns:
        The AssetManifestContext for the current thread/context, or None if not set.

    Performance:
        ~8M ops/sec (benchmarked in rfc-free-threading-patterns.md).
    """
    return _asset_manifest.get()


def set_asset_manifest(ctx: AssetManifestContext) -> Token[AssetManifestContext | None]:
    """Set asset manifest for current context.

    Returns a token that can be used to restore the previous value.
    Always use with try/finally or asset_manifest_context() for proper cleanup.

    Args:
        ctx: The AssetManifestContext to set for the current context.

    Returns:
        Token that can be passed to reset_asset_manifest() to restore previous value.
    """
    return _asset_manifest.set(ctx)


def reset_asset_manifest(token: Token[AssetManifestContext | None] | None = None) -> None:
    """Reset asset manifest context.

    If token is provided, restores to the previous value (proper nesting).
    Otherwise, resets to None.

    Args:
        token: Optional token from set_asset_manifest() for proper nesting support.
    """
    if token is not None:
        _asset_manifest.reset(token)
    else:
        _asset_manifest.set(None)


@contextmanager
def asset_manifest_context(ctx: AssetManifestContext) -> Iterator[AssetManifestContext]:
    """Context manager for scoped asset manifest usage.

    Properly restores previous context on exit (supports nesting).

    Usage:
        manifest = AssetManifest.load(output_dir / "asset-manifest.json")
        ctx = AssetManifestContext(
            entries={k: v.output_path for k, v in manifest.entries.items()},
            mtime=manifest_path.stat().st_mtime,
        )

        with asset_manifest_context(ctx):
            # All parallel page rendering happens here
            # Each thread reads from ContextVar - no locks needed
            render_pages_parallel(pages)

    Args:
        ctx: The AssetManifestContext to use within the context.

    Yields:
        The context that was set (same as input).
    """
    token = set_asset_manifest(ctx)
    try:
        yield ctx
    finally:
        reset_asset_manifest(token)


# =============================================================================
# Asset URL Resolution
# =============================================================================


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

    Uses ContextVar for thread-safe manifest access (no locks needed).
    Falls back to loading manifest from disk if ContextVar is not set.

    Thread Safety (Free-Threading / PEP 703):
        Primary path uses ContextVar - thread-local by design.
        Fallback path loads from disk (safe but slower).

    Args:
        logical_path: Logical asset path (e.g., 'css/style.css')
        site: Site instance

    Returns:
        Fingerprinted output path (e.g., 'assets/css/style.abc123.css') or None
    """
    # Primary path: Use ContextVar (thread-safe, no locks, ~8M ops/sec)
    ctx = get_asset_manifest()
    if ctx is not None:
        return ctx.entries.get(logical_path)

    # Fallback path: Load from disk (for dev server, tests, or when context not set)
    # This is slower but safe - used when asset_manifest_context() wasn't set up
    from bengal.assets.manifest import AssetManifest

    manifest_path = site.output_dir / "asset-manifest.json"
    if not manifest_path.exists():
        return None

    manifest = AssetManifest.load(manifest_path)
    if manifest is None:
        return None

    entry = manifest.get(logical_path)
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


def clear_manifest_cache(site: Site | None = None) -> None:
    """
    Clear the asset manifest cache.

    With ContextVar pattern, this resets the thread-local manifest to None.
    The site parameter is kept for backward compatibility but is not used.

    Args:
        site: Unused (kept for backward compatibility)
    """
    reset_asset_manifest()
