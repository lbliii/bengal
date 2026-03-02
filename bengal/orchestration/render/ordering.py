"""
Page ordering and sorting for render orchestration.

Provides ordering strategies for page rendering:
- Priority sort: changed files first for fast feedback
- Complexity sort: heavy pages first (LPT scheduling) to minimize stragglers
- Track dependency sort: track items before track pages that embed them

These are mixed into RenderOrchestrator via OrderingMixin.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.normalize import to_posix

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


def _normalize_content_path(path: str) -> str:
    """Normalize path for track item matching (same logic as get_page cache key)."""
    normalized = to_posix(path)
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("content/"):
        normalized = normalized[8:]
    return normalized


class OrderingMixin:
    """
    Mixin providing page ordering strategies for RenderOrchestrator.

    Expects from host class:
        site: Site instance
        _get_max_workers() -> int | None (RenderOrchestrator provides this)
    """

    site: Site

    def _get_max_workers(self) -> int | None:
        """Expected from host. RenderOrchestrator overrides with config lookup."""
        return None

    def _should_use_complexity_ordering(self) -> bool:
        """Check if complexity-based ordering is enabled."""
        return self.site.config.get("build", {}).get("complexity_ordering", True)

    def _should_use_track_dependency_ordering(self) -> bool:
        """Check if track dependency ordering is enabled."""
        return self.site.config.get("build", {}).get("track_dependency_ordering", True)

    def _maybe_sort_by_complexity(self, pages: list[Page], max_workers: int) -> list[Page]:
        """Sort pages by complexity if enabled and beneficial.

        When track_dependency_ordering is also enabled, preserves partition order
        (track_items before track_pages before other) and sorts by complexity
        within each partition. This avoids the complexity sort undoing track order.

        Only sorts if:
        1. Complexity ordering is enabled in config (default: True)
        2. We have more pages than workers (otherwise no benefit)

        Heavy pages are sorted first within each partition to minimize stragglers.
        """
        if not self._should_use_complexity_ordering():
            return pages

        if len(pages) <= max_workers:
            return pages

        from bengal.orchestration.complexity import (
            ComplexityStats,
            get_complexity_stats,
            sort_by_complexity,
        )

        track_item_paths = None
        if self._should_use_track_dependency_ordering():
            track_item_paths = self._get_track_item_paths()

        if track_item_paths:
            track_items, track_pages, other = self._partition_by_track(pages, track_item_paths)
            if track_items or track_pages:
                sorted_pages = (
                    sort_by_complexity(track_items, descending=True)
                    + sort_by_complexity(track_pages, descending=True)
                    + sort_by_complexity(other, descending=True)
                )
                logger.debug(
                    "track_dependency_ordering",
                    track_items_count=len(track_items),
                    track_pages_count=len(track_pages),
                    other_count=len(other),
                )
            else:
                sorted_pages = sort_by_complexity(pages, descending=True)
        else:
            sorted_pages = sort_by_complexity(pages, descending=True)

        complexity_stats: ComplexityStats = get_complexity_stats(sorted_pages)
        mean_score = complexity_stats["mean"]
        variance_ratio = complexity_stats["variance_ratio"]
        logger.debug(
            "complexity_distribution",
            page_count=complexity_stats["count"],
            min_score=complexity_stats["min"],
            max_score=complexity_stats["max"],
            mean_score=round(mean_score, 1),
            variance_ratio=round(variance_ratio, 1),
        )
        if variance_ratio > 10:
            logger.debug(
                "complexity_ordering_beneficial",
                reason="high variance detected",
                top_5=complexity_stats["top_5_scores"],
                bottom_5=complexity_stats["bottom_5_scores"],
            )

        return sorted_pages

    def _get_track_item_paths(self) -> set[str] | None:
        """Get normalized track item paths from site.data.tracks, or None if no tracks."""
        tracks_data = getattr(self.site.data, "tracks", None)
        if not tracks_data or not isinstance(tracks_data, dict):
            return None
        paths: set[str] = set()
        for track_def in tracks_data.values():
            if not isinstance(track_def, dict):
                continue
            items = track_def.get("items")
            if not isinstance(items, (list, tuple)):
                continue
            for item in items:
                if isinstance(item, str):
                    paths.add(_normalize_content_path(item))
        return paths if paths else None

    def _get_track_item_paths_for_pages(self, pages: list[Page]) -> set[str]:
        """Get track item paths for tracks that have a page in the given list."""
        tracks_data = getattr(self.site.data, "tracks", None)
        if not tracks_data or not isinstance(tracks_data, dict):
            return set()
        priority_track_ids: set[str] = set()
        for page in pages:
            is_track_page = (
                page.metadata.get("template") == "tracks/single.html"
                or page.metadata.get("track_id") is not None
            )
            if not is_track_page:
                continue
            track_id = page.metadata.get("track_id") or (getattr(page, "slug", None) or "")
            if track_id:
                priority_track_ids.add(track_id)
        if not priority_track_ids:
            return set()
        result: set[str] = set()
        for track_id in priority_track_ids:
            track_def = tracks_data.get(track_id)
            if not isinstance(track_def, dict):
                continue
            items = track_def.get("items")
            if not isinstance(items, (list, tuple)):
                continue
            for item in items:
                if isinstance(item, str):
                    norm = _normalize_content_path(item)
                    result.add(norm)
                    if norm.endswith(".md"):
                        result.add(norm[:-3])
                    else:
                        result.add(f"{norm}.md")
        return result

    def _partition_by_track(
        self, pages: list[Page], track_item_paths: set[str]
    ) -> tuple[list[Page], list[Page], list[Page]]:
        """Partition pages into track_items, track_pages, other."""
        content_root = self.site.root_path / "content"
        track_items: list[Page] = []
        track_pages: list[Page] = []
        other: list[Page] = []

        for page in pages:
            if not page.source_path:
                other.append(page)
                continue
            try:
                rel = page.source_path.relative_to(content_root)
            except ValueError:
                other.append(page)
                continue
            rel_str = to_posix(rel)
            rel_no_ext = rel_str[:-3] if rel_str.endswith(".md") else rel_str
            is_track_item = rel_str in track_item_paths or rel_no_ext in track_item_paths
            is_track_page = (
                page.metadata.get("template") == "tracks/single.html"
                or page.metadata.get("track_id") is not None
            )
            if is_track_item:
                track_items.append(page)
            elif is_track_page:
                track_pages.append(page)
            else:
                other.append(page)

        return track_items, track_pages, other

    def _track_dependency_sort(self, pages: list[Page]) -> list[Page]:
        """
        Sort pages so track items are rendered before track pages that embed them.

        Used by tests. The main render flow uses _maybe_sort_by_complexity which
        integrates partition + complexity in a single pass.

        Returns:
            Pages reordered: track_items first, then track_pages, then other.
        """
        if not self._should_use_track_dependency_ordering():
            return pages
        track_item_paths = self._get_track_item_paths()
        if not track_item_paths:
            return pages
        track_items, track_pages, other = self._partition_by_track(pages, track_item_paths)
        if track_items or track_pages:
            return track_items + track_pages + other
        return pages

    def _priority_sort(self, pages: list[Page], changed_sources: set[Path] | None) -> list[Page]:
        """
        Sort pages so that explicitly changed files are at the front.

        Args:
            pages: Pages to sort
            changed_sources: Set of paths that were explicitly changed

        Returns:
            Prioritized list of pages
        """
        if not changed_sources:
            return pages

        priority_pages: list[Page] = []
        normal_pages: list[Page] = []

        resolved_changed = set()
        for p in changed_sources:
            try:
                resolved_changed.add(p.resolve())
            except (OSError, ValueError):
                resolved_changed.add(p)

        for page in pages:
            is_priority = False
            try:
                if page.source_path and page.source_path.resolve() in resolved_changed:
                    is_priority = True

                if (
                    not is_priority
                    and page.metadata.get("is_autodoc")
                    and page.source_path
                    and page.source_path.resolve() in resolved_changed
                ):
                    is_priority = True
            except (OSError, ValueError):
                if page.source_path in changed_sources:
                    is_priority = True

            if is_priority:
                priority_pages.append(page)
            else:
                normal_pages.append(page)

        if not priority_pages:
            return pages

        if self._should_use_track_dependency_ordering():
            track_item_paths = self._get_track_item_paths()
            if track_item_paths:
                priority_track_item_paths = self._get_track_item_paths_for_pages(priority_pages)
                if priority_track_item_paths:
                    content_root = self.site.root_path / "content"
                    for page in list(normal_pages):
                        if not page.source_path:
                            continue
                        try:
                            rel = page.source_path.relative_to(content_root)
                        except ValueError:
                            continue
                        rel_str = to_posix(rel)
                        rel_no_ext = rel_str[:-3] if rel_str.endswith(".md") else rel_str
                        if (
                            rel_str in priority_track_item_paths
                            or rel_no_ext in priority_track_item_paths
                        ):
                            normal_pages.remove(page)
                            priority_pages.append(page)
                    track_items, track_pages, other = self._partition_by_track(
                        priority_pages, track_item_paths
                    )
                    priority_pages = track_items + track_pages + other

        logger.debug(
            "rendering_prioritization",
            priority_count=len(priority_pages),
            normal_count=len(normal_pages),
        )
        max_workers = self._get_max_workers() or 4
        priority_pages = self._maybe_sort_by_complexity(priority_pages, max_workers)
        normal_pages = self._maybe_sort_by_complexity(normal_pages, max_workers)

        return priority_pages + normal_pages
