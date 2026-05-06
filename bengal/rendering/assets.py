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

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from bengal.rendering.utils.contextvar import ContextVarManager
from bengal.utils.concurrency.thread_local import ThreadSafeSet
from bengal.utils.observability.logger import get_logger
from bengal.utils.observability.observability import ComponentStats
from bengal.utils.paths.normalize import to_posix


class AssetSiteLike(Protocol):
    """Minimal protocol for site objects used in asset resolution."""

    @property
    def output_dir(self) -> Path:
        """Output directory for the site."""
        ...

    @property
    def baseurl(self) -> str:
        """Base URL for the site."""
        ...


logger = get_logger(__name__)

# =============================================================================
# Observability: Fallback Warning Deduplication
# RFC: rfc-asset-resolution-observability.md (Phase 1)
# Thread-safe: Uses ThreadSafeSet for safe concurrent access (PEP 703)
# =============================================================================

# Track paths that have already warned about fallback (avoid log spam)
_fallback_warned: ThreadSafeSet = ThreadSafeSet()

# Phase 3: Aggregated fallback diagnostics (summarized at phase end, not per-asset)
_MAX_FALLBACK_SAMPLES = 5


class _FallbackAggregator:
    """Thread-safe aggregator for unexpected asset manifest fallbacks."""

    def __init__(self) -> None:
        self._count = 0
        self._samples: list[str] = []
        self._lock = threading.Lock()
        self._first_logged = False

    def record(self, logical_path: str) -> None:
        with self._lock:
            self._count += 1
            if len(self._samples) < _MAX_FALLBACK_SAMPLES and logical_path not in self._samples:
                self._samples.append(logical_path)

    def drain(self) -> tuple[int, list[str]]:
        with self._lock:
            count, samples = self._count, list(self._samples)
            self._count = 0
            self._samples.clear()
            self._first_logged = False
            return count, samples

    def should_log_first_debug(self) -> bool:
        with self._lock:
            if self._first_logged or self._count == 0:
                return False
            self._first_logged = True
            return True


_fallback_aggregator = _FallbackAggregator()


# =============================================================================
# Asset Manifest Context (Thread-Safe via ContextVar)
# =============================================================================

__all__ = [
    "AssetManifestContext",
    "asset_manifest_context",
    "clear_manifest_cache",
    "drain_asset_fallback_aggregator",
    "get_asset_manifest",
    "get_asset_manifest_revision",
    # Observability exports (Phase 2)
    "get_resolution_stats",
    "reset_asset_manifest",
    "resolve_asset_url",
    "set_asset_manifest",
]

# =============================================================================
# Observability: Stats Tracking (ContextVarManager-based)
# RFC: rfc-asset-resolution-observability.md (Phase 2)
# =============================================================================

# Thread-safe stats via ContextVarManager
_resolution_stats: ContextVarManager[ComponentStats] = ContextVarManager("resolution_stats")


def get_resolution_stats() -> ComponentStats | None:
    """Get resolution stats for current context (thread-safe).

    Returns:
        ComponentStats instance if resolution has occurred, None otherwise.

    Thread Safety:
        Uses ContextVarManager - each thread/context has independent stats.
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


# Thread-local manifest via ContextVarManager (default None for graceful fallback)
_asset_manifest: ContextVarManager[AssetManifestContext] = ContextVarManager("asset_manifest")


def get_asset_manifest() -> AssetManifestContext | None:
    """Get current asset manifest context (thread-local).

    Returns:
        The AssetManifestContext for the current thread/context, or None if not set.

    Performance:
        ~8M ops/sec (benchmarked in rfc-free-threading-patterns.md).
    """
    return _asset_manifest.get()


def set_asset_manifest(ctx: AssetManifestContext):
    """Set asset manifest for current context.

    Returns a token that can be used to restore the previous value.
    Always use with try/finally or asset_manifest_context() for proper cleanup.

    Args:
        ctx: The AssetManifestContext to set for the current context.

    Returns:
        Token that can be passed to reset_asset_manifest() to restore previous value.
    """
    return _asset_manifest.set(ctx)


def reset_asset_manifest(token=None) -> None:
    """Reset asset manifest context.

    If token is provided, restores to the previous value (proper nesting).
    Otherwise, resets to None.

    Args:
        token: Optional token from set_asset_manifest() for proper nesting support.
    """
    _asset_manifest.reset(token)


def asset_manifest_context(ctx: AssetManifestContext):
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
    return _asset_manifest(ctx)


def get_asset_manifest_revision(site: AssetSiteLike | None = None) -> str | None:
    """Return the current asset manifest revision for cache key namespacing.

    Fragment caches can outlive a single page render. If a cached fragment
    contains ``asset_url()``, its output depends on the active asset manifest.
    Namespacing fragment keys by this revision prevents a cache hit from
    replaying URLs from an older manifest.
    """
    ctx = get_asset_manifest()
    if ctx is not None:
        if ctx.mtime is not None:
            return f"context-mtime:{ctx.mtime}"
        if ctx.entries:
            import hashlib

            digest = hashlib.sha256()
            for logical_path, output_path in sorted(ctx.entries.items()):
                digest.update(logical_path.encode("utf-8", "surrogateescape"))
                digest.update(b"\0")
                digest.update(output_path.encode("utf-8", "surrogateescape"))
                digest.update(b"\0")
            return f"context-entries:{digest.hexdigest()[:16]}"
        return "context-empty"

    if site is None or getattr(site, "dev_mode", False):
        return None

    manifest_path = site.output_dir / "asset-manifest.json"
    try:
        stat = manifest_path.stat()
    except OSError:
        return None
    return f"file:{stat.st_mtime_ns}:{stat.st_size}"


# =============================================================================
# Asset URL Resolution
# =============================================================================


def resolve_asset_url(
    asset_path: str,
    site: AssetSiteLike,
    page: Any = None,
    manifest_ctx: AssetManifestContext | None = None,
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
        manifest_ctx: Optional explicit manifest (Phase 2: used before ContextVar, then fallback)

    Returns:
        Resolved asset URL ready for use in HTML

    Example:
            >>> resolve_asset_url('css/style.css', site)
            '/bengal/assets/css/style.abc123.css'  # Fingerprinted
            >>> resolve_asset_url('css/style.css', site)  # Dev mode
            '/bengal/assets/css/style.css'  # Non-fingerprinted

    """
    from bengal.rendering.utils.url import apply_baseurl

    if not asset_path:
        url = apply_baseurl("/assets/", site)
    else:
        # Normalize path
        clean_path = to_posix(asset_path).strip().lstrip("/")

        baseurl_value = (site.baseurl or "").rstrip("/")

        # Handle file:// protocol - generate relative URLs
        if baseurl_value.startswith("file://"):
            url = _resolve_file_protocol(clean_path, site, page)
        # In dev server mode, prefer stable URLs without fingerprints
        elif getattr(site, "dev_mode", False):
            url = apply_baseurl(f"/assets/{clean_path}", site)
        else:
            # Look up fingerprinted path from manifest (explicit ctx, then ContextVar, then fallback)
            fingerprinted_path = _resolve_fingerprinted(clean_path, site, manifest_ctx=manifest_ctx)
            if fingerprinted_path:
                url = apply_baseurl(f"/{fingerprinted_path}", site)
            else:
                # Fallback: return direct asset path
                url = apply_baseurl(f"/assets/{clean_path}", site)

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


def _resolve_fingerprinted(
    logical_path: str,
    site: AssetSiteLike,
    manifest_ctx: AssetManifestContext | None = None,
) -> str | None:
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
    # Resolver order: explicit context first, then ContextVar, then disk fallback (Phase 2)
    ctx = manifest_ctx if manifest_ctx is not None else get_asset_manifest()
    stats = _ensure_resolution_stats()

    if ctx is not None:
        # Primary path: ContextVar (fast, thread-safe)
        stats.cache_hits += 1
        return ctx.entries.get(logical_path)

    # Fallback path: Disk I/O
    stats.cache_misses += 1

    dev_mode = getattr(site, "dev_mode", False)
    if not dev_mode:
        # Unexpected fallback - aggregate for summarized diagnostics at phase end (Phase 3)
        stats.items_skipped["unexpected_fallback"] = (
            stats.items_skipped.get("unexpected_fallback", 0) + 1
        )
        _fallback_aggregator.record(logical_path)
        # One optional debug event for first fallback (debbuggability)
        if _fallback_aggregator.should_log_first_debug():
            logger.debug(
                "asset_manifest_first_fallback",
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


def _resolve_file_protocol(asset_path: str, site: AssetSiteLike, page: Any = None) -> str:
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
            return f"./{asset_url_path}"
        except ValueError, AttributeError:
            pass

    # Fallback: assume root-level
    return f"./{asset_url_path}"


def drain_asset_fallback_aggregator() -> tuple[int, list[str]]:
    """
    Drain fallback aggregator and return (count, sample_paths).

    Call at phase end (after render/postprocess) to get summarized diagnostics.
    Clears the aggregator for the next build.

    Returns:
        (unexpected_fallback_count, sample_logical_paths)

    Plan: asset-manifest-context-refactor Phase 3
    """
    return _fallback_aggregator.drain()


def clear_manifest_cache(site: AssetSiteLike | None = None) -> None:
    """
    Clear the asset manifest cache and reset observability state.

    With ContextVarManager pattern, this resets the thread-local manifest to None.
    Also resets resolution stats and fallback warning deduplication.
    The site parameter is kept for backward compatibility but is not used.

    Thread-safe: Uses ThreadSafeSet.clear() for safe concurrent access (PEP 703).

    RFC: rfc-asset-resolution-observability.md

    Args:
        site: Unused (kept for backward compatibility)
    """
    reset_asset_manifest()
    _resolution_stats.reset()
    _fallback_warned.clear()
    _fallback_aggregator.drain()
