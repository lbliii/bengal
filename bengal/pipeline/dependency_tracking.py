"""
Stream-based dependency tracking for reactive pipeline.

Replaces DependencyTracker with stream-aware dependency tracking that integrates
with StreamCache for automatic invalidation.

Key Concepts:
    - Dependency tracking: Template and partial dependencies per page
    - Stream integration: Dependencies stored in StreamCache
    - Automatic invalidation: Template changes update dependent stream item versions
    - Fine-grained reactivity: Only affected nodes recompute

Related:
    - bengal/pipeline/cache.py - StreamCache implementation
    - bengal/cache/dependency_tracker.py - Legacy DependencyTracker (being replaced)
    - bengal/rendering/pipeline.py - RenderingPipeline using dependency tracking
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.pipeline.cache import StreamCache
from bengal.pipeline.core import StreamKey
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


class StreamDependencyTracker:
    """
    Stream-aware dependency tracker that integrates with StreamCache.

    Tracks template, partial, and config dependencies during rendering and
    stores them in StreamCache. When dependencies change, automatically
    invalidates dependent stream items by updating their versions.

    Key Differences from DependencyTracker:
        - Uses StreamCache instead of BuildCache
        - Stores dependencies as part of stream item metadata
        - Automatic invalidation via stream version updates
        - Fine-grained reactivity (only affected nodes recompute)

    Creation:
        Direct instantiation: StreamDependencyTracker(cache, site)
            - Created by pipeline for dependency tracking
            - Requires StreamCache instance
            - Requires Site instance for config path access

    Attributes:
        cache: StreamCache instance for dependency storage
        site: Site instance for config path access
        logger: Logger instance
        current_page: Thread-local current page being processed
        dependencies: Forward dependency graph (page → dependencies)
        reverse_dependencies: Reverse dependency graph (dependency → pages)

    Thread Safety:
        Thread-safe. Uses thread-local storage for current page tracking.

    Examples:
        tracker = StreamDependencyTracker(cache, site)
        tracker.start_page(page.source_path)
        tracker.track_template(template_path)
        tracker.end_page()
    """

    def __init__(self, cache: StreamCache, site: Site) -> None:
        """
        Initialize stream dependency tracker.

        Args:
            cache: StreamCache instance for dependency storage
            site: Site instance for config path access
        """
        self.cache = cache
        self.site = site
        self.logger = get_logger(__name__)
        self.dependencies: dict[Path, set[Path]] = {}
        self.reverse_dependencies: dict[Path, set[Path]] = {}
        self.lock = threading.Lock()
        # Use thread-local storage for current page to support parallel processing
        self.current_page = threading.local()

    def _get_page_stream_key(self, page_path: Path) -> StreamKey | None:
        """
        Get StreamKey for a page.

        Args:
            page_path: Path to the page

        Returns:
            StreamKey for the page or None if not found
        """
        # Try to find the page's stream key in cache
        # Pages are cached with source="create_page" and id=relative_path
        try:
            content_dir = self.site.root_path / "content"
            rel_path = page_path.relative_to(content_dir)
            # Try to find cached entry
            # This is a simplified lookup - in practice, we'd need to track
            # the mapping from page paths to stream keys
            return StreamKey(
                source="create_page",
                id=str(rel_path),
                version="",  # Will be updated when dependency changes
            )
        except ValueError:
            return None

    def start_page(self, page_path: Path) -> None:
        """
        Mark the start of processing a page (thread-safe).

        Args:
            page_path: Path to the page being processed
        """
        self.current_page.value = page_path
        # Initialize dependency set for this page
        with self.lock:
            if page_path not in self.dependencies:
                self.dependencies[page_path] = set()

    def track_template(self, template_path: Path) -> None:
        """
        Record that the current page depends on a template (thread-safe).

        Args:
            template_path: Path to the template file
        """
        if not hasattr(self.current_page, "value"):
            return

        page_path = self.current_page.value

        with self.lock:
            # Add to forward dependencies
            self.dependencies.setdefault(page_path, set()).add(template_path)

            # Add to reverse dependencies
            self.reverse_dependencies.setdefault(template_path, set()).add(page_path)

        # Store dependency in cache metadata
        self._store_dependency(page_path, template_path)

    def track_partial(self, partial_path: Path) -> None:
        """
        Record that the current page depends on a partial/include (thread-safe).

        Args:
            partial_path: Path to the partial file
        """
        if not hasattr(self.current_page, "value"):
            return

        page_path = self.current_page.value

        with self.lock:
            self.dependencies.setdefault(page_path, set()).add(partial_path)
            self.reverse_dependencies.setdefault(partial_path, set()).add(page_path)

        self._store_dependency(page_path, partial_path)

    def track_config(self, config_path: Path) -> None:
        """
        Record that the current page depends on the config file (thread-safe).

        All pages depend on config, so this marks it as a global dependency.

        Args:
            config_path: Path to the config file
        """
        if not hasattr(self.current_page, "value"):
            return

        page_path = self.current_page.value

        with self.lock:
            self.dependencies.setdefault(page_path, set()).add(config_path)
            self.reverse_dependencies.setdefault(config_path, set()).add(page_path)

        self._store_dependency(page_path, config_path)

    def track_asset(self, asset_path: Path) -> None:
        """
        Record an asset file (for cache invalidation).

        Args:
            asset_path: Path to the asset file
        """
        # Assets don't create dependencies, just track for invalidation
        pass

    def track_taxonomy(self, page_path: Path, tags: set[str]) -> None:
        """
        Record taxonomy (tags/categories) dependencies.

        When a page's tags change, tag pages need to be regenerated.

        Args:
            page_path: Path to the page
            tags: Set of tags/categories for this page
        """
        # Taxonomy dependencies are handled by taxonomy stream
        # This is kept for compatibility
        pass

    def end_page(self) -> None:
        """Mark the end of processing a page (thread-safe)."""
        if hasattr(self.current_page, "value"):
            del self.current_page.value

    def _store_dependency(self, page_path: Path, dependency_path: Path) -> None:
        """
        Store dependency in stream cache metadata.

        Args:
            page_path: Path to the page
            dependency_path: Path to the dependency (template, partial, etc.)
        """
        # Store dependency metadata in cache
        # This allows us to query which pages depend on a given template
        # The actual invalidation happens when templates change (see invalidate_dependency)
        pass

    def invalidate_dependency(self, dependency_path: Path) -> set[Path]:
        """
        Invalidate all pages that depend on a given template/partial/config.

        When a dependency changes, this updates the version of all dependent
        stream items, causing them to be recomputed.

        Args:
            dependency_path: Path to the changed dependency

        Returns:
            Set of page paths that were invalidated
        """
        with self.lock:
            affected_pages = self.reverse_dependencies.get(dependency_path, set()).copy()

        # Update version of affected stream items
        # This causes them to be recomputed on next build
        for page_path in affected_pages:
            self._invalidate_page(page_path)

        return affected_pages

    def _invalidate_page(self, page_path: Path) -> None:
        """
        Invalidate a page by updating its stream version.

        Args:
            page_path: Path to the page to invalidate
        """
        # For now, we'll mark the page as needing recomputation
        # The actual invalidation will happen when the stream tries to use it
        # This is a placeholder - full implementation would update StreamCache entries
        logger.debug("page_invalidated", page_path=str(page_path))

    def get_dependencies(self, page_path: Path) -> set[Path]:
        """
        Get all dependencies for a page.

        Args:
            page_path: Path to the page

        Returns:
            Set of dependency paths
        """
        with self.lock:
            return self.dependencies.get(page_path, set()).copy()

    def get_dependent_pages(self, dependency_path: Path) -> set[Path]:
        """
        Get all pages that depend on a given dependency.

        Args:
            dependency_path: Path to the dependency

        Returns:
            Set of page paths
        """
        with self.lock:
            return self.reverse_dependencies.get(dependency_path, set()).copy()
