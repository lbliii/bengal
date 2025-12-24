"""
Version-related change detection for incremental builds.

Handles cross-version link dependencies and version scope filtering
for versioned documentation sites.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import DependencyTracker
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.orchestration.build.results import ChangeSummary

logger = get_logger(__name__)


class VersionChangeDetector:
    """
    Handles version-related change detection.

    RFC: rfc-versioned-docs-pipeline-integration

    Provides:
    - Cross-version link dependency tracking
    - Version scope filtering for focused rebuilds
    """

    def __init__(
        self,
        site: Site,
        tracker: DependencyTracker,
    ) -> None:
        """
        Initialize version change detector.

        Args:
            site: Site instance for version configuration
            tracker: DependencyTracker for cross-version dependencies
        """
        self.site = site
        self.tracker = tracker
        # Note: Page lookup uses site.page_by_source_path (shared cache)

    def _get_page_by_path(self, path: Path) -> Page | None:
        """O(1) page lookup by source path (uses site-level cache)."""
        # Use site-level cache to avoid duplicate O(P) builds across orchestrators
        # See: plan/drafted/rfc-orchestration-package-optimizations.md (Phase 1)
        return self.site.page_by_source_path.get(path)

    def apply_cross_version_rebuilds(
        self,
        *,
        pages_to_rebuild: set[Path],
        verbose: bool,
        change_summary: ChangeSummary,
    ) -> int:
        """
        Add pages that depend on changed cross-version link targets.

        RFC: rfc-versioned-docs-pipeline-integration (Phase 2)

        When a page changes that is the target of cross-version links ([[v2:path]]),
        the source pages containing those links must be rebuilt to update their
        link text (which may include the target's title).

        Args:
            pages_to_rebuild: Set of page paths to rebuild (modified in place)
            verbose: Whether to collect detailed change information
            change_summary: Summary object to record changes

        Returns:
            Count of pages added due to cross-version dependencies.
        """
        # Check if versioning is enabled
        if not getattr(self.site, "versioning_enabled", False):
            return 0

        # Check if tracker supports cross-version dependencies
        if not hasattr(self.tracker, "get_cross_version_dependents"):
            return 0

        added_count = 0
        xver_sources: set[Path] = set()

        # For each page being rebuilt, check if other pages have cross-version links to it
        for changed_path in list(pages_to_rebuild):
            # Find the page to get its version
            # PERF: O(1) lookup instead of O(n) scan
            page = self._get_page_by_path(changed_path)
            if not page:
                continue

            # Get the page's version
            version = getattr(page, "version", None) or page.metadata.get("version")
            if not version:
                continue

            # Normalize the path for lookup (remove content/ prefix if present)
            # Cross-version links use paths like [[v2:docs/guide]] without content/ prefix
            path_str = str(changed_path)
            content_prefix = str(self.site.root_path / "content") + "/"
            if path_str.startswith(content_prefix):
                path_str = path_str[len(content_prefix) :]

            # Remove version prefix from path (e.g., docs/v2/guide -> docs/guide)
            # This matches how cross-version links are stored
            version_config = getattr(self.site, "version_config", None)
            if version_config:
                for section in getattr(version_config, "sections", []):
                    section_prefix = f"{section}/{version}/"
                    if path_str.startswith(section_prefix):
                        path_str = section + "/" + path_str[len(section_prefix) :]
                        break

            # Remove .md extension
            if path_str.endswith(".md"):
                path_str = path_str[:-3]

            # Also handle index pages
            if path_str.endswith("/_index"):
                path_str = path_str[:-7]
            elif path_str.endswith("/index"):
                path_str = path_str[:-6]

            # Get pages that have cross-version links to this target
            dependents = self.tracker.get_cross_version_dependents(
                changed_version=version,
                changed_path=path_str,
            )

            for dependent_path in dependents:
                if dependent_path not in pages_to_rebuild:
                    xver_sources.add(dependent_path)

        # Add dependent pages to rebuild set
        for source_path in xver_sources:
            pages_to_rebuild.add(source_path)
            added_count += 1

            if verbose:
                change_summary.extra_changes.setdefault("Cross-version dependencies", [])
                change_summary.extra_changes["Cross-version dependencies"].append(
                    f"Rebuilt {source_path.name} (cross-version link target changed)"
                )

        return added_count

    def apply_version_scope_filter(self, pages: list[Page]) -> list[Page]:
        """
        Filter pages to only include those in the specified version scope.

        RFC: rfc-versioned-docs-pipeline-integration (Phase 3)

        When version_scope is set in config, only pages belonging to that version
        are rebuilt. This speeds up focused development on a single version.

        Args:
            pages: List of pages to filter

        Returns:
            Filtered list of pages (only those matching version_scope, or all if not set)
        """
        # Get version_scope from site config
        version_scope = self.site.config.get("_version_scope")
        if not version_scope:
            return pages

        # Check if versioning is enabled
        if not getattr(self.site, "versioning_enabled", False):
            return pages

        # Resolve version aliases (e.g., "latest" -> actual version id)
        version_config = getattr(self.site, "version_config", None)
        if not version_config:
            return pages

        target_version = version_config.get_version_or_alias(version_scope)
        if not target_version:
            logger.warning(
                "version_scope_unknown",
                version_scope=version_scope,
                action="rebuilding_all_versions",
            )
            return pages

        target_version_id = target_version.id
        filtered_pages: list[Page] = []

        for page in pages:
            # Get page's version
            page_version = getattr(page, "version", None) or page.metadata.get("version")

            # Include page if:
            # 1. It's not versioned (shared content, non-versioned sections)
            # 2. It matches the target version
            if page_version is None or page_version == target_version_id:
                filtered_pages.append(page)

        if len(filtered_pages) < len(pages):
            logger.info(
                "version_scope_filter_applied",
                version_scope=version_scope,
                resolved_version=target_version_id,
                total_pages=len(pages),
                filtered_pages=len(filtered_pages),
                skipped_pages=len(pages) - len(filtered_pages),
            )

        return filtered_pages
