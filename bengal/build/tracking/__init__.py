"""
Dependency tracking for incremental builds.
"""

from __future__ import annotations

from bengal.build.tracking.tracker import CacheInvalidator, DependencyTracker

__all__ = ["CacheInvalidator", "DependencyTracker"]
