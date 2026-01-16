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
RFC: rfc-asset-resolution-observability.md (Observability)
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

from bengal.utils.concurrency.thread_local import ThreadSafeSet
from bengal.utils.observability.logger import get_logger
from bengal.utils.observability.observability import ComponentStats

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)

# =============================================================================
# Observability: Fallback Warning Deduplication
# RFC: rfc-asset-resolution-observability.md (Phase 1)
# Thread-safe: Uses ThreadSafeSet for safe concurrent access (PEP 703)
# =============================================================================

# Track paths that have already warned about fallback (avoid log spam)
_fallback_warned: ThreadSafeSet = ThreadSafeSet()


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
    # Observability exports (Phase 2)
    "get_resolution_stats",
]

# =============================================================================
# Observability: Stats Tracking (ContextVar-based)
# RFC: rfc-asset-resolution-observability.md (Phase 2)
# =============================================================================

# Thread-safe stats via ContextVar (matches manifest pattern)
_resolution_stats: ContextVar[ComponentStats | None] = ContextVar(
    "resolution_stats", default=None
)


def get_resolution_stats() -> ComponentStats | None:
    """Get resolution stats for current context (thread-safe).

    Returns:
        ComponentStats instance if resolution has occurred, None otherwise.

    Thread Safety:
        Uses ContextVar - each thread/context has independent stats.
    """
    return _resolution_stats.get()


def _ensure_resolution_stats() -> ComponentStats:
    """Get or create resolution stats for current context.

    Returns:
        ComponentStats instance for tracking resolution metrics.
    """
    stats = _resolution_stats.get()
    if stats is None:
        stats = ComponentStats()
        _resolution_stats.set(stats)
    return stats


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
    
    RFC: rfc-build-performance-optimizations Phase 2
    Tracks asset references during render-time if AssetTracker is active.
    
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
        url = with_baseurl("/assets/", site)
    else:
        # Normalize path
        clean_path = asset_path.replace("\\", "/").strip().lstrip("/")

        baseurl_value = (site.baseurl or "").rstrip("/")

        # Handle file:// protocol - generate relative URLs
        if baseurl_value.startswith("file://"):
            url = _resolve_file_protocol(clean_path, site, page)
        # In dev server mode, prefer stable URLs without fingerprints
        elif getattr(site, "dev_mode", False):
            url = with_baseurl(f"/assets/{clean_path}", site)
        else:
            # Look up fingerprinted path from manifest
            fingerprinted_path = _resolve_fingerprinted(clean_path, site)
            if fingerprinted_path:
                url = with_baseurl(f"/{fingerprinted_path}", site)
            else:
                # Fallback: return direct asset path
                url = with_baseurl(f"/assets/{clean_path}", site)
    
    # RFC: rfc-build-performance-optimizations Phase 2
    # Track asset reference if tracker is active (render-time tracking)
    tracker = _get_asset_tracker()
    if tracker:
        # Track the original logical path, not the resolved URL
        # (the logical path is what we need for dependency tracking)
        tracker.track(asset_path if asset_path else "/assets/")
    
    return url


def _get_asset_tracker() -> Any | None:
    """Get current asset tracker if available.
    
    Returns:
        Current AssetTracker instance, or None
    """
    try:
        from bengal.rendering.asset_tracking import get_current_tracker
        return get_current_tracker()
    except ImportError:
        # Graceful degradation if module not available
        return None


def _resolve_fingerprinted(logical_path: str, site: Site) -> str | None:
    """
    Resolve a logical asset path to its fingerprinted output path.

    Uses ContextVar for thread-safe manifest access (no locks needed).
    Falls back to loading manifest from disk if ContextVar is not set.

    Thread Safety (Free-Threading / PEP 703):
        Primary path uses ContextVar - thread-local by design.
        Fallback path loads from disk (safe but slower).
        Stats tracking uses ContextVar - no global mutable state.

    RFC: rfc-asset-resolution-observability.md

    Args:
        logical_path: Logical asset path (e.g., 'css/style.css')
        site: Site instance

    Returns:
        Fingerprinted output path (e.g., 'assets/css/style.abc123.css') or None
    """
    global _fallback_warned

    # Primary path: Use ContextVar (thread-safe, no locks, ~8M ops/sec)
    ctx = get_asset_manifest()
    stats = _ensure_resolution_stats()

    if ctx is not None:
        # Primary path: ContextVar (fast, thread-safe)
        stats.cache_hits += 1
        return ctx.entries.get(logical_path)

    # Fallback path: Disk I/O
    stats.cache_misses += 1

    dev_mode = getattr(site, "dev_mode", False)
    if not dev_mode:
        # Unexpected fallback - warn (suggests missing context setup)
        stats.items_skipped["unexpected_fallback"] = (
            stats.items_skipped.get("unexpected_fallback", 0) + 1
        )
        # Warn once per unique path to avoid log spam during render
        # Thread-safe: add_if_new returns True if item was new (not present before)
        if _fallback_warned.add_if_new(logical_path):
            logger.warning(
                "asset_manifest_disk_fallback",
                logical_path=logical_path,
                output_dir=str(site.output_dir),
                hint="ContextVar not set - was asset_manifest_context() called?",
            )
    else:
        # Expected fallback in dev mode
        stats.items_skipped["dev_mode_fallback"] = (
            stats.items_skipped.get("dev_mode_fallback", 0) + 1
        )
        logger.debug(
            "asset_manifest_dev_mode_fallback",
            logical_path=logical_path,
        )

    # Load from disk (for dev server, tests, or when context not set)
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
    Clear the asset manifest cache and reset observability state.

    With ContextVar pattern, this resets the thread-local manifest to None.
    Also resets resolution stats and fallback warning deduplication.
    The site parameter is kept for backward compatibility but is not used.

    Thread-safe: Uses ThreadSafeSet.clear() for safe concurrent access (PEP 703).

    RFC: rfc-asset-resolution-observability.md

    Args:
        site: Unused (kept for backward compatibility)
    """
    reset_asset_manifest()
    _resolution_stats.set(None)
    _fallback_warned.clear()