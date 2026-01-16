"""
Render-time asset tracking for performance optimization.

RFC: rfc-build-performance-optimizations Phase 2
Tracks assets during template rendering to avoid post-render HTML parsing.

This module provides a context-local asset tracker that can be used during
template rendering to collect asset references. This eliminates the need to
parse HTML after rendering to extract asset dependencies.

Thread Safety:
Uses ContextVar for thread-local storage, making it safe for parallel rendering.
Each thread/context has its own tracker instance.

Usage:
    # In rendering pipeline
    tracker = AssetTracker()
    with tracker:
        # Render template - asset_url() calls will track assets
        html = render_template(template, context)
    
    # Get tracked assets
    assets = tracker.get_assets()
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Context-local tracker for thread safety
_current_tracker: ContextVar[AssetTracker | None] = ContextVar("asset_tracker", default=None)


class AssetTracker:
    """
    Track assets during template rendering (no HTML parsing).
    
    Thread-safe via ContextVar - each thread/context has independent tracker.
    
    Usage:
        tracker = AssetTracker()
        with tracker:
            # Render template - asset_url() will track assets
            html = render_template(...)
        
        assets = tracker.get_assets()
    """
    
    __slots__ = ("_assets",)
    
    def __init__(self) -> None:
        """Initialize empty asset tracker."""
        self._assets: set[str] = set()
    
    def track(self, path: str) -> None:
        """Track an asset reference.
        
        Args:
            path: Asset path/URL to track
        """
        if path:
            self._assets.add(path)
    
    def get_assets(self) -> set[str]:
        """Get all tracked asset paths.
        
        Returns:
            Copy of tracked asset set
        """
        return self._assets.copy()
    
    def __enter__(self) -> AssetTracker:
        """Enter context manager - set as current tracker."""
        _current_tracker.set(self)
        return self
    
    def __exit__(self, *_: object) -> None:
        """Exit context manager - clear current tracker."""
        _current_tracker.set(None)


def get_current_tracker() -> AssetTracker | None:
    """Get the current asset tracker (if any).
    
    Returns:
        Current AssetTracker instance, or None if not in tracking context
    """
    return _current_tracker.get()
