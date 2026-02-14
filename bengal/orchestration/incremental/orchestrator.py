"""
Main IncrementalOrchestrator coordinating incremental build components.

This module provides the IncrementalOrchestrator class that coordinates
cache management, change detection, and rebuild filtering through the
unified EffectBasedDetector.

Key Concepts:
- Unified change detection: Uses EffectBasedDetector for all dependency tracking
- Phase-based detection: Early (pre-taxonomy) and full (post-taxonomy)

Related Modules:
- bengal.orchestration.incremental.cache_manager: Cache operations
- bengal.orchestration.incremental.effect_detector: Unified change detection
- bengal.orchestration.incremental.cleanup: Deleted file cleanup
- bengal.core.nav_tree: NavTreeCache for cached navigation

RFC: Aggressive Cleanup
- Replaced 8 legacy detector classes with EffectBasedDetector
- Eliminated DetectionPipeline in favor of direct detector usage

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.orchestration.build.results import ChangeSummary
from bengal.orchestration.build_context import BuildContext
from bengal.orchestration.incremental.cache_manager import CacheManager
from bengal.orchestration.incremental.cleanup import cleanup_deleted_files
from bengal.orchestration.incremental.effect_detector import (
    EffectBasedDetector,
    create_detector_from_build,
)
from bengal.utils.cache_registry import InvalidationReason, invalidate_for_reason
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.effects.tracer import EffectTracer
    from bengal.orchestration.build.coordinator import CacheCoordinator

logger = get_logger(__name__)


class IncrementalOrchestrator:
    """
    Orchestrates incremental build logic for efficient rebuilds.

    Coordinates cache management, change detection, dependency tracking, and
    selective rebuilding using the unified EffectBasedDetector. Uses file hashes,
    dependency graphs, and taxonomy indexes to minimize rebuild work.

    Component Delegation:
        - CacheManager: Cache loading, saving, and migration
        - EffectBasedDetector: Unified change detection (replaces old pipeline)
        - cleanup: Deleted file cleanup

    Creation:
        Direct instantiation: IncrementalOrchestrator(site)
            - Created by BuildOrchestrator when incremental builds enabled
            - Requires Site instance with content populated

    Attributes:
        site: Site instance for incremental builds
        cache: BuildCache instance for build state persistence
        effect_tracer: EffectTracer for effect-based dependency tracking
        _cache_manager: CacheManager instance for cache operations
        _detector: EffectBasedDetector instance for change detection

    Example:
            >>> orchestrator = IncrementalOrchestrator(site)
            >>> cache = orchestrator.initialize(enabled=True)
            >>> pages, assets, summary = orchestrator.find_work_early()

    """

    def __init__(self, site: Site) -> None:
        """
        Initialize incremental orchestrator.

        Args:
            site: Site instance for incremental builds
        """
        self.site = site
        self.cache: BuildCache | None = None
        self.coordinator: CacheCoordinator | None = None
        self.effect_tracer: EffectTracer | None = None

        # Component instances
        self._cache_manager = CacheManager(site)
        self._detector: EffectBasedDetector | None = None

    def initialize(self, enabled: bool = False) -> BuildCache:
        """
        Initialize cache and EffectTracer for incremental builds.

        Delegates to CacheManager for cache operations.

        Args:
            enabled: Whether incremental builds are enabled

        Returns:
            BuildCache instance
        """
        self.cache = self._cache_manager.initialize(enabled)
        # Expose coordinator for use by detectors
        self.coordinator = self._cache_manager.coordinator
        # Expose EffectTracer for dependency tracking
        self.effect_tracer = self._cache_manager.effect_tracer
        # Create unified detector from effect tracer
        self._detector = create_detector_from_build(self.site)
        return self.cache

    def check_config_changed(self) -> bool:
        """
        Check if configuration has changed (requires full rebuild).

        Delegates to CacheManager for config validation. If config changed,
        uses centralized cache registry to invalidate all CONFIG_CHANGED caches.

        Returns:
            True if config changed (cache was invalidated)
        """
        # Sync cache state with cache manager
        self._cache_manager.cache = self.cache
        config_changed = self._cache_manager.check_config_changed()

        if config_changed:
            # Use centralized cache registry for coordinated invalidation
            # This replaces manual NavTreeCache.invalidate() + invalidate_version_page_index()
            invalidated = invalidate_for_reason(InvalidationReason.CONFIG_CHANGED)
            logger.debug("caches_invalidated", reason="config_changed", caches=invalidated)

            # Invalidate site version dict caches (site.versions, site.latest_version)
            # These cache .to_dict() results for template performance
            # Note: Site caches aren't in the registry (they're instance-level, not global)
            if hasattr(self.site, "invalidate_version_caches"):
                self.site.invalidate_version_caches()
                logger.debug("site_version_dict_cache_invalidated", reason="config_changed")

        return config_changed

    def find_work_early(
        self,
        verbose: bool = False,
        forced_changed_sources: set[Path] | None = None,
        nav_changed_sources: set[Path] | None = None,
    ) -> tuple[list[Page], list[Asset], ChangeSummary]:
        """
        Find pages/assets that need rebuilding (early phase - before taxonomy).

        This is called BEFORE taxonomies/menus are generated, so it only checks
        content/asset changes. Generated pages will be determined later.

        Invalidates NavTreeCache when structural changes are detected:
        - New pages added
        - Pages deleted
        - Navigation-affecting metadata changed (title, weight, icon)

        Args:
            verbose: Whether to collect detailed change information
            forced_changed_sources: Paths explicitly changed (from watcher)
            nav_changed_sources: Paths with navigation-affecting changes

        Returns:
            Tuple of (pages_to_build, assets_to_process, change_summary)
        """
        if not self.cache:
            from bengal.errors import BengalError, ErrorCode

            raise BengalError(
                "Cache not initialized - call initialize() first",
                code=ErrorCode.B010,
                suggestion="Call IncrementalOrchestrator.initialize() before use",
            )

        # Use EffectBasedDetector for change detection
        changed_paths = forced_changed_sources or set()
        if nav_changed_sources:
            changed_paths = changed_paths | nav_changed_sources

        pages_to_rebuild, content_changed, all_changed = self._detect_changes(
            changed_paths, verbose=verbose
        )

        # Detect cascade changes and track for summary (use all_changed, not input)
        cascade_changes = self._get_cascade_changes_for_summary(all_changed)

        # Invalidate caches if structural changes detected
        has_structural_changes = bool(content_changed) or bool(nav_changed_sources)
        if has_structural_changes:
            invalidated = invalidate_for_reason(InvalidationReason.STRUCTURAL_CHANGE)
            logger.debug("caches_invalidated", reason="structural_changes", caches=invalidated)

        # Check for template changes
        template_changes = self._detect_template_changes()

        # Convert paths to page/asset objects
        # Pass changed_paths for proper asset change detection via file watcher
        pages_to_build_objs, assets_to_process = self._convert_paths_to_objects(
            pages_to_rebuild, changed_paths=changed_paths
        )

        extra_changes: dict[str, list[Any]] = {}
        if cascade_changes:
            extra_changes["Cascade changes"] = cascade_changes

        change_summary = ChangeSummary(
            modified_content=list(content_changed),
            modified_assets=[a.source_path for a in assets_to_process],
            modified_templates=template_changes,
            taxonomy_changes=[],
            extra_changes=extra_changes,
        )

        return pages_to_build_objs, assets_to_process, change_summary

    def _get_cascade_changes_for_summary(self, changed_paths: set[Path]) -> list[str]:
        """Get cascade change descriptions for the summary."""
        cascade_info: list[str] = []
        page_by_path = self.site.page_by_source_path

        for path in changed_paths:
            if path.suffix != ".md":
                continue
            page = page_by_path.get(path)
            if page and page.metadata.get("cascade"):
                cascade_info.append(f"Cascade from {path.name}")

        return cascade_info

    def _detect_template_changes(self) -> list[Path]:
        """Detect changed templates."""
        template_changes: list[Path] = []

        # Check theme templates directory
        templates_dir = self._cache_manager._get_theme_templates_dir()
        if templates_dir and templates_dir.exists():
            template_changes.extend(
                template_file
                for template_file in templates_dir.rglob("*.html")
                if self.cache and self.cache.is_changed(template_file)
            )

        return template_changes

    def _detect_template_affected_pages(self) -> set[Path]:
        """
        Get pages affected by template changes.

        Uses cache.get_affected_pages() to find pages that use changed templates.
        """
        affected_pages: set[Path] = set()

        # Check theme templates directory
        templates_dir = self._cache_manager._get_theme_templates_dir()
        if not templates_dir or not templates_dir.exists():
            return affected_pages

        for template_file in templates_dir.rglob("*.html"):
            if (
                self.cache
                and self.cache.is_changed(template_file)
                and hasattr(self.cache, "get_affected_pages")
            ):
                # Get pages affected by this template
                affected_paths = self.cache.get_affected_pages(str(template_file))
                for path_str in affected_paths:
                    affected_pages.add(Path(path_str))

        return affected_pages

    def find_work(self, verbose: bool = False) -> tuple[list[Page], list[Asset], ChangeSummary]:
        """
        Find pages/assets that need rebuilding (full phase - after taxonomy).

        This is called AFTER taxonomies/menus are generated, so it can include
        generated pages in the rebuild set based on tag changes.

        Args:
            verbose: Whether to collect detailed change information

        Returns:
            Tuple of (pages_to_build, assets_to_process, change_summary)
        """
        if not self.cache:
            from bengal.errors import BengalError, ErrorCode

            raise BengalError(
                "Cache not initialized - call initialize() first",
                code=ErrorCode.B010,
                suggestion="Call IncrementalOrchestrator.initialize() before use",
            )

        # In full phase, we detect additional changes including generated pages
        pages_to_rebuild, content_changed, _all_changed = self._detect_changes(
            set(), verbose=verbose
        )

        # Convert paths to page/asset objects
        pages_to_build_objs, assets_to_process = self._convert_paths_to_objects(pages_to_rebuild)

        change_summary = ChangeSummary(
            modified_content=list(content_changed),
            modified_assets=[a.source_path for a in assets_to_process],
            modified_templates=[],
            taxonomy_changes=[],
        )

        return pages_to_build_objs, assets_to_process, change_summary

    def _detect_changes(
        self,
        changed_paths: set[Path],
        *,
        verbose: bool = False,
    ) -> tuple[set[Path], set[Path], set[Path]]:
        """
        Detect pages that need rebuilding using EffectBasedDetector.

        Handles:
        - Direct content changes
        - Cascade propagation (pages with cascade mark all descendants)
        - Template changes (rebuild affected pages)
        - Taxonomy tracking for dependency management

        Args:
            changed_paths: Paths explicitly changed
            verbose: Whether to log detailed info

        Returns:
            Tuple of (pages_to_rebuild, content_changed, all_changed)
        """
        if self._detector is None:
            self._detector = create_detector_from_build(self.site)

        # Also check for cache-based changes (files modified since last build)
        all_changed: set[Path] = set(changed_paths)
        for page in self.site.pages:
            if page.metadata.get("_generated"):
                continue
            if self.cache and self.cache.should_bypass(page.source_path):
                all_changed.add(page.source_path)

        # Use EffectBasedDetector for change detection
        pages_to_rebuild = self._detector.detect_changes(all_changed, verbose=verbose)

        # Track taxonomy for changed pages (for dependency management)
        for path in all_changed:
            if path.suffix == ".md":
                # Taxonomy tracking now handled by EffectTracer via
                # Effect.for_taxonomy_page() during rendering
                pass

        # Handle cascade changes - pages with cascade mark all descendants
        cascade_pages = self._detect_cascade_changes(all_changed, verbose=verbose)
        pages_to_rebuild.update(cascade_pages)

        # Handle nav metadata changes - when _index.md nav metadata changes,
        # all section pages should rebuild
        nav_affected = self._detect_nav_metadata_changes(all_changed, verbose=verbose)
        pages_to_rebuild.update(nav_affected)

        # Handle template changes - add affected pages
        template_affected = self._detect_template_affected_pages()
        pages_to_rebuild.update(template_affected)

        # Content changed = intersection of changed and markdown files
        content_changed = {p for p in all_changed if p.suffix == ".md"}

        return pages_to_rebuild, content_changed, all_changed

    def _detect_cascade_changes(
        self,
        changed_paths: set[Path],
        *,
        verbose: bool = False,
    ) -> set[Path]:
        """
        Detect pages affected by cascade changes.

        When a page with `cascade` metadata changes, all pages in its section
        and subsections need rebuilding.

        Args:
            changed_paths: Paths that changed
            verbose: Whether to log detailed info

        Returns:
            Set of additional pages that need rebuilding due to cascade
        """
        cascade_rebuild: set[Path] = set()
        page_by_path = self.site.page_by_source_path

        for path in changed_paths:
            if path.suffix != ".md":
                continue

            page = page_by_path.get(path)
            if not page:
                continue

            cascade = page.metadata.get("cascade")
            if not cascade:
                continue

            # Page has cascade - mark all pages in same section and subsections
            # Find the section this page belongs to
            for section in self.site.sections:
                if hasattr(section, "index_page") and section.index_page is page:
                    # This is a section index with cascade - mark all section pages
                    for section_page in section.pages:
                        cascade_rebuild.add(section_page.source_path)
                    # Also mark subsection pages
                    self._add_subsection_pages(section, cascade_rebuild)
                    break
                elif hasattr(section, "pages") and page in section.pages:
                    # Regular page with cascade in a section
                    for section_page in section.pages:
                        cascade_rebuild.add(section_page.source_path)
                    break
            else:
                # No section found - this might be a root-level page
                # Root-level cascade affects all pages
                for p in self.site.pages:
                    cascade_rebuild.add(p.source_path)

        return cascade_rebuild

    def _add_subsection_pages(self, section: Any, rebuild_set: set[Path]) -> None:
        """Recursively add pages from subsections."""
        if not hasattr(section, "subsections"):
            return
        for subsection in section.subsections:
            if hasattr(subsection, "pages"):
                for page in subsection.pages:
                    rebuild_set.add(page.source_path)
            self._add_subsection_pages(subsection, rebuild_set)

    def _detect_nav_metadata_changes(
        self,
        changed_paths: set[Path],
        *,
        verbose: bool = False,
    ) -> set[Path]:
        """
        Detect pages affected by navigation metadata changes.

        When an _index.md file's nav metadata (title, weight, icon) changes,
        all pages in that section need rebuilding since they display navigation.

        Args:
            changed_paths: Paths that changed
            verbose: Whether to log detailed info

        Returns:
            Set of additional pages that need rebuilding due to nav changes
        """
        import json

        from bengal.orchestration.constants import extract_nav_metadata
        from bengal.utils.primitives.hashing import hash_str

        nav_rebuild: set[Path] = set()
        page_by_path = self.site.page_by_source_path

        for path in changed_paths:
            # Only process _index.md files (section nav files)
            if path.name != "_index.md":
                continue

            page = page_by_path.get(path)
            if not page:
                continue

            # Get current nav metadata hash
            metadata = page.metadata or {}
            nav_meta = extract_nav_metadata(metadata)
            current_hash = hash_str(json.dumps(nav_meta, sort_keys=True, default=str))

            # Get cached nav metadata hash
            cached_hash = None
            if self.cache and hasattr(self.cache, "parsed_content"):
                cached_data = self.cache.parsed_content.get(str(path), {})
                cached_hash = cached_data.get("nav_metadata_hash")

            # If nav metadata changed, rebuild all section pages
            if cached_hash is not None and cached_hash != current_hash:
                # Find section for this _index.md and mark all its pages
                for section in self.site.sections:
                    if (hasattr(section, "index_page") and section.index_page is page) or (
                        hasattr(section, "path") and section.path == path.parent
                    ):
                        if hasattr(section, "pages"):
                            for section_page in section.pages:
                                nav_rebuild.add(section_page.source_path)
                        break

        return nav_rebuild

    def _convert_paths_to_objects(
        self,
        pages_to_rebuild: set[Path],
        changed_paths: set[Path] | None = None,
    ) -> tuple[list[Page], list[Asset]]:
        """
        Convert source paths to Page/Asset objects.

        Args:
            pages_to_rebuild: Set of page source paths to rebuild
            changed_paths: Optional set of explicitly changed paths from file watcher.
                Used for fast-path asset change detection.

        Returns:
            Tuple of (pages_to_build, assets_to_process)
        """
        pages_by_path = self.site.page_by_source_path

        pages_to_build: list[Page] = []
        for path in pages_to_rebuild:
            page = pages_by_path.get(path)
            if page is None:
                # Fallback to scan when cache map isn't populated
                page = next((p for p in self.site.pages if p.source_path == path), None)
            if page is not None:
                pages_to_build.append(page)

        # Check for changed assets - pass changed_paths for fast-path detection
        # This ensures file watcher changes are properly communicated to asset detection
        assets_to_process: list[Asset] = [
            asset
            for asset in self.site.assets
            if self.cache
            and self.cache.should_bypass(asset.source_path, changed_sources=changed_paths)
        ]

        return pages_to_build, assets_to_process

    def process(self, change_type: str, changed_paths: set[str]) -> None:
        """
        Bridge-style process for testing incremental invalidation.

        ⚠️  TEST BRIDGE ONLY - See docstring for details.
        Uses EffectTracer for change detection.
        """
        if not self.cache:
            from bengal.errors import BengalError, ErrorCode

            raise BengalError(
                "Cache not initialized - call initialize() first",
                code=ErrorCode.B010,
                suggestion="Call IncrementalOrchestrator.initialize() before use",
            )

        import sys

        if "pytest" not in sys.modules:
            logger.warning(
                "IncrementalOrchestrator.process() is a test bridge. "
                "Use run() or full_build() for production builds."
            )

        context = BuildContext(site=self.site, pages=self.site.pages)

        path_set: set[Path] = {Path(p) for p in changed_paths}

        # Use EffectTracer for invalidation
        from bengal.effects.render_integration import BuildEffectTracer

        tracer = BuildEffectTracer.get_instance().tracer
        invalidated = tracer.outputs_needing_rebuild(path_set)

        for path in invalidated:
            self._write_output(path, context)

    def _write_output(self, path: Path, context: BuildContext) -> None:
        """Write placeholder output for test bridge."""
        import datetime

        content_dir = self.site.root_path / "content"
        rel: Path | str
        try:
            rel = path.relative_to(content_dir)
        except ValueError:
            rel = path.name

        from pathlib import Path as _P

        rel_html = _P(rel).with_suffix(".html")
        if rel_html.stem in ("index", "_index"):
            rel_html = rel_html.parent / "index.html"
        else:
            rel_html = rel_html.parent / rel_html.stem / "index.html"

        output_path = self.site.output_dir / rel_html
        output_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().isoformat()
        diagnostic_content = (
            f"[TEST BRIDGE] Updated at {timestamp}\nSource: {path}\nOutput: {rel_html}"
        )
        output_path.write_text(diagnostic_content)

    def full_rebuild(self, pages: list[Any], context: BuildContext) -> None:
        """Full rebuild placeholder (unused)."""

    def _cleanup_deleted_files(self) -> None:
        """Clean up output files for deleted source files."""
        if self.cache:
            cleanup_deleted_files(self.site, self.cache)

    def save_cache(self, pages_built: list[Page], assets_processed: list[Asset]) -> None:
        """
        Update cache with processed files.

        Delegates to CacheManager. Also saves EffectTracer state.

        Args:
            pages_built: Pages that were built
            assets_processed: Assets that were processed
        """
        self._cache_manager.cache = self.cache
        # Sync EffectTracer back to CacheManager for persistence
        self._cache_manager._effect_tracer = self.effect_tracer
        self._cache_manager.save(pages_built, assets_processed)

    def _check_shared_content_changes(
        self, forced_changed_sources: set[Path] | None = None
    ) -> bool:
        """
        Check if any _shared/ content has changed.

        When shared content changes, ALL versioned pages need rebuilding since
        shared content is injected into every version.

        Args:
            forced_changed_sources: Optional set of paths explicitly changed

        Returns:
            True if any shared content has changed
        """
        if not self.site.versioning_enabled:
            return False

        if not self.cache:
            return False

        version_config = getattr(self.site, "version_config", None)
        if not version_config:
            return False

        # Check if any forced changes are in shared paths
        content_dir = self.site.root_path / "content"
        if forced_changed_sources:
            for path in forced_changed_sources:
                for shared_path in version_config.shared:
                    shared_dir = content_dir / shared_path
                    try:
                        path.relative_to(shared_dir)
                        return True  # Path is in shared dir
                    except ValueError:
                        continue

        # Check if any shared files have changed via cache
        for shared_path in version_config.shared:
            shared_dir = content_dir / shared_path
            if not shared_dir.exists():
                continue

            for file_path in shared_dir.rglob("*.md"):
                if self.cache.is_changed(file_path):
                    return True

        return False
