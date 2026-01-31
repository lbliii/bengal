"""
Render-time asset tracking for performance optimization.

RFC: rfc-build-performance-optimizations Phase 2
Tracks assets during template rendering to avoid post-render HTML parsing.

This module provides a context-local asset tracker that can be used during
template rendering to collect asset references. This eliminates the need to
parse HTML after rendering to extract asset dependencies.

Thread Safety:
Uses ContextVarManager for thread-local storage, making it safe for parallel rendering.
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

from typing import Any

from bengal.rendering.utils.contextvar import ContextVarManager

# Context-local tracker for thread safety using ContextVarManager
_current_tracker: ContextVarManager[AssetTracker] = ContextVarManager("asset_tracker")


class AssetTracker:
    """
    Track assets during template rendering (no HTML parsing).

    Thread-safe via ContextVarManager - each thread/context has independent tracker.

    Supports nesting: inner trackers restore the outer tracker on exit.

    Usage:
        tracker = AssetTracker()
        with tracker:
            # Render template - asset_url() will track assets
            html = render_template(...)

        assets = tracker.get_assets()

    Nested usage:
        with outer_tracker:
            with inner_tracker:
                # inner_tracker is active
                pass
            # outer_tracker is restored
    """

    __slots__ = ("_assets", "_token")

    def __init__(self) -> None:
        """Initialize empty asset tracker."""
        self._assets: set[str] = set()
        self._token: Any = None

    def track(self, path: str) -> None:
        """Track an asset reference.

        Empty strings and whitespace-only strings are ignored.

        Args:
            path: Asset path/URL to track
        """
        # Strip whitespace and check for empty - whitespace-only paths are invalid
        if path and path.strip():
            self._assets.add(path)

    def get_assets(self) -> set[str]:
        """Get all tracked asset paths.

        Returns:
            Copy of tracked asset set
        """
        return self._assets.copy()

    def __enter__(self) -> AssetTracker:
        """Enter context manager - set as current tracker, saving previous."""
        self._token = _current_tracker.set(self)
        return self

    def __exit__(self, *_: Any) -> None:
        """Exit context manager - restore previous tracker."""
        if self._token is not None:
            _current_tracker.reset(self._token)
            self._token = None


def get_current_tracker() -> AssetTracker | None:
    """Get the current asset tracker (if any).

    Returns:
        Current AssetTracker instance, or None if not in tracking context
    """
    return _current_tracker.get()
