"""
Cache coordinator for unified page-level cache invalidation.

Coordinates invalidation across BuildCache's page-level cache layers:
- rendered_output: Final HTML output
- parsed_content: Parsed markdown + metadata
- file_fingerprints: File mtimes/hashes

Key Concepts:
- Single point of control for all page-level cache operations
- Explicit invalidation cascades (data files, templates, taxonomy)
- Event logging for debugging and observability
- Thread-safe for parallel rendering

Related Modules:
- bengal.cache.build_cache: Cache storage
- bengal.cache.dependency_tracker: Dependency tracking
- bengal.utils.cache_registry: Global cache coordination (complementary)

See Also:
- plan/rfc-cache-invalidation-architecture.md: Design RFC

"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache.build_cache import BuildCache
    from bengal.cache.dependency_tracker import DependencyTracker
    from bengal.core.site import Site

logger = get_logger(__name__)


class PageInvalidationReason(Enum):
    """
    Why a page's caches were invalidated.

    Alignment:
        This enum is aligned with RebuildReasonCode in results.py.
        While RebuildReasonCode tracks why a page was chosen for build,
        this enum tracks why its specific cache layers were cleared.
    """

    CONTENT_CHANGED = auto()  # Source file modified
    DATA_FILE_CHANGED = auto()  # Dependent data file modified
    TEMPLATE_CHANGED = auto()  # Template or partial modified
    TAXONOMY_CASCADE = auto()  # Member page metadata changed
    ASSET_CHANGED = auto()  # Dependent asset modified
    CONFIG_CHANGED = auto()  # Site config modified
    MANUAL = auto()  # Explicit invalidation request
    FULL_BUILD = auto()  # Full rebuild requested
    OUTPUT_MISSING = auto()  # Cached output exists but file missing on disk


@dataclass
class InvalidationEvent:
    """Record of a cache invalidation."""

    page_path: Path
    reason: PageInvalidationReason
    trigger: str  # What caused the invalidation (e.g., "data/team.yaml")
    caches_cleared: list[str] = field(default_factory=list)


# Maximum events to retain (prevents unbounded memory for large sites)
_MAX_EVENTS = 10_000


class CacheCoordinator:
    """
    Coordinates cache invalidation across page-level cache layers.

    Ensures that when any dependency changes, ALL affected caches
    are properly invalidated in the correct order.

    Scope:
        - Manages: BuildCache.parsed_content, rendered_output, file_fingerprints
        - Does NOT manage: Global caches (use cache_registry.py instead)

    Thread Safety:
        All public methods are thread-safe. Uses Lock for event logging
        since rendering may happen in parallel.

    Related:
        - cache_registry.py: Global cache coordination (complementary)
        - DependencyTracker: Tracks dependencies; this class acts on them

    Example:
        >>> coordinator = CacheCoordinator(cache, tracker, site)
        >>> coordinator.invalidate_page(
        ...     page_path,
        ...     PageInvalidationReason.DATA_FILE_CHANGED,
        ...     trigger="data/team.yaml",
        ... )
    """

    def __init__(
        self,
        cache: BuildCache,
        tracker: DependencyTracker,
        site: Site,
    ) -> None:
        """
        Initialize the cache coordinator.

        Args:
            cache: BuildCache instance for cache operations
            tracker: DependencyTracker for dependency lookups
            site: Site instance for page access
        """
        self.cache = cache
        self.tracker = tracker
        self.site = site
        self._events: list[InvalidationEvent] = []
        self._lock = Lock()

    def invalidate_page(
        self,
        page_path: Path,
        reason: PageInvalidationReason,
        trigger: str = "",
    ) -> InvalidationEvent:
        """
        Invalidate all caches for a single page.

        This is the ONLY way caches should be invalidated for pages.
        Ensures all layers are cleared consistently.

        Args:
            page_path: Path to the page source file
            reason: Why the page is being invalidated
            trigger: What caused the invalidation (for logging)

        Returns:
            InvalidationEvent with list of caches that were actually cleared.
        """
        event = InvalidationEvent(
            page_path=page_path,
            reason=reason,
            trigger=trigger,
        )

        # Layer 1: Rendered output (final HTML)
        if self.cache.invalidate_rendered_output(page_path):
            event.caches_cleared.append("rendered_output")

        # Layer 2: Parsed content (markdown AST + metadata)
        if self.cache.invalidate_parsed_content(page_path):
            event.caches_cleared.append("parsed_content")

        # Layer 3: File fingerprint
        if self.cache.invalidate_fingerprint(page_path):
            event.caches_cleared.append("fingerprint")

        # Thread-safe event logging with bounds
        with self._lock:
            self._events.append(event)
            # Trim to prevent unbounded growth on large sites
            if len(self._events) > _MAX_EVENTS:
                self._events = self._events[-_MAX_EVENTS:]

        if event.caches_cleared:
            logger.debug(
                "cache_invalidated",
                page=str(page_path),
                reason=reason.name,
                trigger=trigger,
                caches=event.caches_cleared,
            )

        return event

    def invalidate_for_data_file(self, data_file: Path) -> list[InvalidationEvent]:
        """
        Invalidate all pages that depend on a data file.

        Called when data/*.yaml or data/*.json changes.

        Args:
            data_file: Path to the changed data file

        Returns:
            List of InvalidationEvents for affected pages
        """
        events: list[InvalidationEvent] = []
        affected_pages = self.tracker.get_pages_using_data_file(data_file)

        for page_path in affected_pages:
            event = self.invalidate_page(
                page_path,
                reason=PageInvalidationReason.DATA_FILE_CHANGED,
                trigger=str(data_file),
            )
            events.append(event)

        if events:
            logger.info(
                "data_file_invalidation",
                data_file=str(data_file),
                affected_pages=len(events),
            )

        return events

    def invalidate_for_template(self, template_path: Path) -> list[InvalidationEvent]:
        """
        Invalidate all pages that use a template.

        Called when templates/*.html changes.

        Args:
            template_path: Path to the changed template file

        Returns:
            List of InvalidationEvents for affected pages
        """
        events: list[InvalidationEvent] = []
        affected_pages = self.cache.get_affected_pages(template_path)

        for page_path_str in affected_pages:
            page_path = Path(page_path_str)
            event = self.invalidate_page(
                page_path,
                reason=PageInvalidationReason.TEMPLATE_CHANGED,
                trigger=str(template_path),
            )
            events.append(event)

        if events:
            logger.info(
                "template_invalidation",
                template=str(template_path),
                affected_pages=len(events),
            )

        return events

    def invalidate_taxonomy_cascade(
        self,
        member_page: Path,
        term_pages: set[Path],
    ) -> list[InvalidationEvent]:
        """
        Invalidate taxonomy term pages when a member's metadata changes.

        Called when a post's title/date/summary changes and the
        taxonomy listing pages need to reflect the new values.

        Args:
            member_page: Path to the member page that changed
            term_pages: Set of term page paths to invalidate

        Returns:
            List of InvalidationEvents for affected term pages
        """
        events: list[InvalidationEvent] = []

        for term_page in term_pages:
            event = self.invalidate_page(
                term_page,
                reason=PageInvalidationReason.TAXONOMY_CASCADE,
                trigger=str(member_page),
            )
            events.append(event)

        if events:
            logger.info(
                "taxonomy_cascade_invalidation",
                member_page=str(member_page),
                term_pages=len(events),
            )

        return events

    def invalidate_all(
        self,
        reason: PageInvalidationReason = PageInvalidationReason.FULL_BUILD,
    ) -> int:
        """
        Invalidate all caches (full rebuild).

        Args:
            reason: Reason for the full invalidation

        Returns:
            Count of pages invalidated.
        """
        count = 0
        for page in self.site.pages:
            self.invalidate_page(page.source_path, reason, trigger="full_build")
            count += 1

        logger.info(
            "full_cache_invalidation",
            reason=reason.name,
            pages_invalidated=count,
        )

        return count

    @property
    def events(self) -> list[InvalidationEvent]:
        """Thread-safe access to events (returns copy)."""
        with self._lock:
            return list(self._events)

    def get_invalidation_summary(self) -> dict[str, list[dict[str, str | list[str]]]]:
        """
        Get summary of all invalidations for logging/debugging.

        Returns:
            Dictionary mapping reason names to lists of invalidation details
        """
        by_reason: dict[str, list[dict[str, str | list[str]]]] = {}
        with self._lock:
            for event in self._events:
                reason_name = event.reason.name
                if reason_name not in by_reason:
                    by_reason[reason_name] = []
                by_reason[reason_name].append(
                    {
                        "page": str(event.page_path),
                        "trigger": event.trigger,
                        "caches": event.caches_cleared,
                    }
                )
        return by_reason

    def clear_events(self) -> None:
        """Clear event log (call at start of each build)."""
        with self._lock:
            self._events.clear()

    def get_stats(self) -> dict[str, int]:
        """
        Get statistics about invalidations.

        Returns:
            Dictionary with invalidation statistics
        """
        with self._lock:
            by_reason: dict[str, int] = {}
            for event in self._events:
                reason_name = event.reason.name
                by_reason[reason_name] = by_reason.get(reason_name, 0) + 1

            return {
                "total_invalidations": len(self._events),
                **by_reason,
            }
