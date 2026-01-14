"""
Unified change detection for incremental builds.

Provides a single ChangeDetector class that handles both early (pre-taxonomy)
and full (post-taxonomy) change detection, replacing the separate find_work()
and find_work_early() methods.

Key Concepts:
- Phase-based detection: "early" for pre-taxonomy, "full" for post-taxonomy
- Section-level filtering: Skip entire unchanged sections
- Cascade dependencies: Rebuild descendants when cascade metadata changes
- Template dependencies: Track which pages use which templates
- Parallel change detection: ThreadPoolExecutor for large sites (>50 pages)

Related Modules:
- bengal.orchestration.incremental.rebuild_filter: Page/asset filtering
- bengal.orchestration.incremental.cascade_tracker: Cascade dependencies
- bengal.orchestration.incremental.file_detector: Page/asset change detection
- bengal.orchestration.incremental.template_detector: Template change detection
- bengal.orchestration.incremental.taxonomy_detector: Taxonomy/autodoc detection
- bengal.orchestration.incremental.version_detector: Version-related detection
- bengal.cache.dependency_tracker: Template dependencies

Performance:
RFC: rfc-parallel-change-detection
- Uses ThreadPoolExecutor for parallel filesystem operations
- Threshold-based: sequential for small workloads, parallel for large
- Thread-safe result collection with locks

"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from bengal.orchestration.build.results import ChangeSummary
from bengal.orchestration.incremental.cascade_tracker import CascadeTracker
from bengal.orchestration.incremental.data_detector import DataFileDetector
from bengal.orchestration.incremental.file_detector import FileChangeDetector
from bengal.orchestration.incremental.rebuild_filter import RebuildFilter
from bengal.orchestration.incremental.taxonomy_detector import TaxonomyChangeDetector
from bengal.orchestration.incremental.template_detector import TemplateChangeDetector
from bengal.orchestration.incremental.version_detector import VersionChangeDetector
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import BuildCache, DependencyTracker
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site

logger = get_logger(__name__)


@dataclass
class ChangeSet:
    """
    Result of change detection.
    
    Contains all the information about what needs to be rebuilt.
    
    Attributes:
        pages_to_build: Pages that need rebuilding
        assets_to_process: Assets that need processing
        change_summary: Detailed summary of changes
        
    """

    pages_to_build: list[Page] = field(default_factory=list)
    assets_to_process: list[Asset] = field(default_factory=list)
    change_summary: ChangeSummary = field(default_factory=ChangeSummary)


class ChangeDetector:
    """
    Unified change detection for incremental builds.
    
    Replaces the separate find_work() and find_work_early() methods with
    a single detect_changes() method that takes a phase parameter.
    
    Attributes:
        site: Site instance for content access
        cache: BuildCache for change detection
        tracker: DependencyTracker for template dependencies
        rebuild_filter: RebuildFilter for page/asset filtering
        cascade_tracker: CascadeTracker for cascade dependencies
    
    Example:
            >>> detector = ChangeDetector(site, cache, tracker)
            >>> change_set = detector.detect_changes(
            ...     phase="early",
            ...     forced_changed_sources={changed_path},
            ... )
            >>> build_pages(change_set.pages_to_build)
        
    """

    def __init__(
        self,
        site: Site,
        cache: BuildCache,
        tracker: DependencyTracker,
    ) -> None:
        """
        Initialize change detector.

        Args:
            site: Site instance for content access
            cache: BuildCache for change detection
            tracker: DependencyTracker for template dependencies
        """
        self.site = site
        self.cache = cache
        self.tracker = tracker
        self.rebuild_filter = RebuildFilter(site, cache)
        self.cascade_tracker = CascadeTracker(site)

        # Initialize sub-detectors
        self._file_detector = FileChangeDetector(site, cache, tracker)
        self._template_detector = TemplateChangeDetector(site, cache)
        self._taxonomy_detector = TaxonomyChangeDetector(site, cache, tracker)
        self._version_detector = VersionChangeDetector(site, tracker)
        self._data_detector = DataFileDetector(site, cache, tracker)

    def detect_changes(
        self,
        phase: Literal["early", "full"],
        *,
        verbose: bool = False,
        forced_changed_sources: set[Path] | None = None,
        nav_changed_sources: set[Path] | None = None,
    ) -> ChangeSet:
        """
        Detect changes requiring rebuilds.

        Unified method that handles both early (pre-taxonomy) and full
        (post-taxonomy) change detection.

        Args:
            phase: "early" for pre-taxonomy detection, "full" for post-taxonomy
            verbose: Whether to collect detailed change information
            forced_changed_sources: Paths explicitly changed (from file watcher)
            nav_changed_sources: Paths with navigation-affecting changes

        Returns:
            ChangeSet containing pages/assets to rebuild and change summary

        Phase Differences:
            - "early": Called before taxonomy generation. Only checks content/asset
              changes. Generated pages will be determined later based on affected tags.
            - "full": Called after taxonomy generation. Includes tag page rebuilds
              based on tag changes.
        """
        forced_changed = {Path(p) for p in (forced_changed_sources or set())}
        nav_changed = {Path(p) for p in (nav_changed_sources or set())}
        all_changed = forced_changed | nav_changed

        pages_to_rebuild: set[Path] = set()
        assets_to_process: list[Asset] = []
        change_summary = ChangeSummary()

        # Section-level filtering optimization
        changed_sections = self._get_changed_sections(forced_changed, nav_changed)

        # Select pages to check based on section filtering
        pages_to_check = self.rebuild_filter.select_pages_to_check(
            changed_sections=changed_sections,
            forced_changed=forced_changed,
            nav_changed=nav_changed,
        )

        if verbose and changed_sections is not None:
            logger.debug(
                "section_level_filtering",
                total_sections=len(self.site.sections),
                changed_sections=len(changed_sections),
            )

        # Check each page for changes
        self._file_detector.check_pages(
            pages_to_check=pages_to_check,
            changed_sections=changed_sections,
            all_changed=all_changed,
            pages_to_rebuild=pages_to_rebuild,
            change_summary=change_summary,
            verbose=verbose,
        )

        # Apply cascade rebuilds
        cascade_count = self.cascade_tracker.apply_cascade_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            verbose=verbose,
            change_summary=change_summary,
        )
        if cascade_count > 0:
            logger.info(
                "cascade_dependencies_detected",
                additional_pages=cascade_count,
                reason="section_cascade_metadata_changed",
            )

        # Apply shared content cascade (versioned docs)
        self.rebuild_filter.apply_shared_content_cascade(
            pages_to_rebuild=pages_to_rebuild,
            forced_changed=forced_changed,
            verbose=verbose,
            change_summary=change_summary,
        )

        # Apply nav frontmatter section rebuilds
        self.rebuild_filter.apply_nav_frontmatter_section_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            all_changed=all_changed,
            verbose=verbose,
            change_summary=change_summary,
        )

        # RFC: rfc-versioned-docs-pipeline-integration (Phase 2)
        # Apply cross-version link dependencies
        xver_count = self._version_detector.apply_cross_version_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            verbose=verbose,
            change_summary=change_summary,
        )
        if xver_count > 0:
            logger.info(
                "cross_version_dependencies_detected",
                additional_pages=xver_count,
                reason="cross_version_link_targets_changed",
            )

        # Apply adjacent navigation rebuilds
        nav_count = self.cascade_tracker.apply_adjacent_navigation_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            verbose=verbose,
            change_summary=change_summary,
        )
        if nav_count > 0:
            logger.info(
                "navigation_dependencies_detected",
                additional_pages=nav_count,
                reason="adjacent_pages_have_nav_links_to_modified_pages",
            )

        # Check assets
        self._file_detector.check_assets(
            forced_changed=forced_changed,
            assets_to_process=assets_to_process,
            change_summary=change_summary,
            verbose=verbose,
        )

        # Check templates
        self._template_detector.check_templates(
            pages_to_rebuild=pages_to_rebuild,
            change_summary=change_summary,
            verbose=verbose,
        )

        # RFC: rfc-incremental-build-dependency-gaps (Phase 1)
        # Check data file changes
        data_pages_count = self._data_detector.check_data_files(
            pages_to_rebuild=pages_to_rebuild,
            change_summary=change_summary,
            verbose=verbose,
        )
        if data_pages_count > 0:
            logger.info(
                "data_file_dependencies_detected",
                additional_pages=data_pages_count,
                reason="data_files_changed",
            )

        # Phase-specific logic
        if phase == "full":
            # Post-taxonomy: Handle tag page rebuilds
            self._taxonomy_detector.check_taxonomy_changes(
                pages_to_rebuild=pages_to_rebuild,
                change_summary=change_summary,
                verbose=verbose,
            )

            # RFC: rfc-incremental-build-dependency-gaps (Phase 2)
            # Check for member page metadata changes that cascade to term pages
            metadata_cascade_count = self._taxonomy_detector.check_metadata_cascades(
                pages_to_rebuild=pages_to_rebuild,
                change_summary=change_summary,
                verbose=verbose,
            )
            if metadata_cascade_count > 0:
                logger.info(
                    "metadata_cascades_detected",
                    additional_pages=metadata_cascade_count,
                    reason="member_page_metadata_changed",
                )

        # Check autodoc changes
        autodoc_pages = self._taxonomy_detector.check_autodoc_changes(
            change_summary=change_summary,
            verbose=verbose,
        )

        # Convert to Page objects
        pages_to_build = self._collect_pages(pages_to_rebuild, autodoc_pages)

        logger.info(
            "incremental_work_detected",
            phase=phase,
            pages_to_build=len(pages_to_build),
            assets_to_process=len(assets_to_process),
            modified_pages=len(change_summary.modified_content),
            modified_templates=len(change_summary.modified_templates),
            modified_assets=len(change_summary.modified_assets),
            total_pages=len(self.site.pages),
        )

        return ChangeSet(
            pages_to_build=pages_to_build,
            assets_to_process=assets_to_process,
            change_summary=change_summary,
        )

    def _get_changed_sections(
        self,
        forced_changed: set[Path],
        nav_changed: set[Path],
    ) -> set[Section] | None:
        """Get sections that have changed files."""
        if not hasattr(self.site, "sections") or not self.site.sections:
            return None

        changed_sections = self.rebuild_filter.get_changed_sections(self.site.sections)

        # Ensure forced/explicit changes keep their sections in scope
        # PERF: Use cached page lookup from cascade_tracker instead of O(n) scan
        for forced_path in forced_changed | nav_changed:
            forced_page = self.cascade_tracker._get_page_by_path(forced_path)
            sec = getattr(forced_page, "_section", None)
            if sec:
                changed_sections.add(sec)

        return changed_sections

    def _collect_pages(
        self,
        pages_to_rebuild: set[Path],
        autodoc_pages: set[str],
    ) -> list[Page]:
        """Convert page paths to Page objects."""
        has_autodoc_tracking = False
        if hasattr(self.cache, "autodoc_dependencies"):
            with contextlib.suppress(TypeError, AttributeError):
                has_autodoc_tracking = bool(self.cache.autodoc_dependencies)

        pages = [
            page
            for page in self.site.pages
            if (page.source_path in pages_to_rebuild and not page.metadata.get("_generated"))
            or (
                page.metadata.get("is_autodoc")
                and (str(page.source_path) in autodoc_pages or not has_autodoc_tracking)
            )
        ]

        # RFC: rfc-versioned-docs-pipeline-integration (Phase 3)
        # Apply version scope filtering if configured
        return self._version_detector.apply_version_scope_filter(pages)
