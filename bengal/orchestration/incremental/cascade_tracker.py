"""
Cascade dependency tracking for incremental builds.

Tracks cascade metadata changes in section index pages and identifies
descendant pages that need rebuilding when cascade metadata changes.

Key Concepts:
    - Cascade metadata: Frontmatter values that propagate to descendant pages
    - Section rebuilds: When cascade changes, all descendants need rebuild
    - Root cascade: Site-wide cascade affects all pages

Related Modules:
    - bengal.core.section: Section model with cascade support
    - bengal.orchestration.incremental: Incremental build coordination
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.orchestration.build.results import ChangeSummary
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


class CascadeTracker:
    """
    Tracks cascade metadata dependencies for incremental builds.

    When a section index page with cascade metadata changes, all descendant
    pages inherit the metadata and must be rebuilt. This class identifies
    which pages are affected by cascade changes.

    Attributes:
        site: Site instance for page lookup

    Example:
        >>> tracker = CascadeTracker(site)
        >>> affected = tracker.find_cascade_affected_pages(index_page)
        >>> pages_to_rebuild.update(affected)
    """

    def __init__(self, site: Site) -> None:
        """
        Initialize cascade tracker.

        Args:
            site: Site instance for page and section lookup
        """
        self.site = site

    def apply_cascade_rebuilds(
        self,
        *,
        pages_to_rebuild: set[Path],
        verbose: bool,
        change_summary: ChangeSummary,
    ) -> int:
        """
        Expand `pages_to_rebuild` based on cascade metadata changes.

        When a section index page (_index.md or index.md) has "cascade" metadata,
        descendant pages inherit metadata and must be rebuilt.

        Args:
            pages_to_rebuild: Set of page paths to rebuild (modified in place)
            verbose: Whether to collect detailed change information
            change_summary: Summary object to record changes

        Returns:
            Count of newly affected pages added due to cascade expansion.
        """
        cascade_affected_count = 0
        for changed_path in list(pages_to_rebuild):  # Iterate over snapshot
            if changed_path.stem not in ("_index", "index"):
                continue

            changed_page = next((p for p in self.site.pages if p.source_path == changed_path), None)
            if not changed_page or "cascade" not in changed_page.metadata:
                continue

            affected_pages = self._find_cascade_affected_pages(changed_page)
            before_count = len(pages_to_rebuild)
            pages_to_rebuild.update(affected_pages)
            after_count = len(pages_to_rebuild)
            newly_affected = after_count - before_count
            cascade_affected_count += newly_affected

            if verbose and newly_affected > 0:
                change_summary.extra_changes.setdefault("Cascade changes", [])
                change_summary.extra_changes["Cascade changes"].append(
                    f"{changed_path.name} cascade affects {newly_affected} descendant pages"
                )

        return cascade_affected_count

    def _find_cascade_affected_pages(self, index_page: Page) -> set[Path]:
        """
        Find all pages affected by a cascade change in a section index.

        When a section's _index.md has cascade metadata and is modified,
        all descendant pages inherit those values and need to be rebuilt.

        Args:
            index_page: Section _index.md page with cascade metadata

        Returns:
            Set of page source paths that should be rebuilt due to cascade
        """
        affected: set[Path] = set()

        # Check if this is a root-level page (affects ALL pages)
        is_root_level = not any(index_page in section.pages for section in self.site.sections)

        if is_root_level:
            # Root-level cascade affects all pages in the site
            logger.info(
                "root_cascade_change_detected",
                index_page=str(index_page.source_path),
                affected_count="all_pages",
            )
            for page in self.site.pages:
                if not page.metadata.get("_generated"):
                    affected.add(page.source_path)
        else:
            # Find the section that owns this index page
            for section in self.site.sections:
                if section.index_page == index_page:
                    # Get all pages in this section and subsections recursively
                    for page in section.regular_pages_recursive:
                        if not page.metadata.get("_generated"):
                            affected.add(page.source_path)

                    logger.debug(
                        "section_cascade_change_detected",
                        section=section.name,
                        index_page=str(index_page.source_path),
                        affected_count=len(affected),
                    )
                    break

        return affected

    def apply_adjacent_navigation_rebuilds(
        self,
        *,
        pages_to_rebuild: set[Path],
        verbose: bool,
        change_summary: ChangeSummary,
    ) -> int:
        """
        Expand `pages_to_rebuild` for prev/next navigation dependencies.

        When a page changes, adjacent pages may need rebuild because they render
        the changed page's title in prev/next navigation.

        Args:
            pages_to_rebuild: Set of page paths to rebuild (modified in place)
            verbose: Whether to collect detailed change information
            change_summary: Summary object to record changes

        Returns:
            Count of pages added due to adjacent navigation dependencies.
        """
        navigation_affected_count = 0
        for changed_path in list(pages_to_rebuild):  # Iterate over snapshot
            changed_page = next((p for p in self.site.pages if p.source_path == changed_path), None)
            if not changed_page or changed_page.metadata.get("_generated"):
                continue

            if hasattr(changed_page, "prev") and changed_page.prev:
                prev_page = changed_page.prev
                if (
                    not prev_page.metadata.get("_generated")
                    and prev_page.source_path not in pages_to_rebuild
                ):
                    pages_to_rebuild.add(prev_page.source_path)
                    navigation_affected_count += 1
                    if verbose:
                        change_summary.extra_changes.setdefault("Navigation changes", [])
                        change_summary.extra_changes["Navigation changes"].append(
                            f"{prev_page.source_path.name} references modified {changed_path.name}"
                        )

            if hasattr(changed_page, "next") and changed_page.next:
                next_page = changed_page.next
                if (
                    not next_page.metadata.get("_generated")
                    and next_page.source_path not in pages_to_rebuild
                ):
                    pages_to_rebuild.add(next_page.source_path)
                    navigation_affected_count += 1
                    if verbose:
                        change_summary.extra_changes.setdefault("Navigation changes", [])
                        change_summary.extra_changes["Navigation changes"].append(
                            f"{next_page.source_path.name} references modified {changed_path.name}"
                        )

        return navigation_affected_count
