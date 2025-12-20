"""
Main IncrementalOrchestrator coordinating incremental build components.

This module provides the IncrementalOrchestrator class that coordinates
cache management, change detection, and rebuild filtering through specialized
component classes.

Key Concepts:
    - Component delegation: Work delegated to focused component classes
    - Phase-based detection: Early (pre-taxonomy) and full (post-taxonomy)
    - Shadow execution: Optional validation of new logic against legacy

Related Modules:
    - bengal.orchestration.incremental.cache_manager: Cache operations
    - bengal.orchestration.incremental.change_detector: Change detection
    - bengal.orchestration.incremental.cleanup: Deleted file cleanup
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.orchestration.build.results import ChangeSummary
from bengal.orchestration.incremental.cache_manager import CacheManager
from bengal.orchestration.incremental.change_detector import ChangeDetector
from bengal.orchestration.incremental.cleanup import cleanup_deleted_files
from bengal.utils.build_context import BuildContext
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import BuildCache, DependencyTracker
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.site import Site

logger = get_logger(__name__)


class IncrementalOrchestrator:
    """
    Orchestrates incremental build logic for efficient rebuilds.

    Coordinates cache management, change detection, dependency tracking, and
    selective rebuilding through specialized component classes. Uses file hashes,
    dependency graphs, and taxonomy indexes to minimize rebuild work.

    Component Delegation:
        - CacheManager: Cache loading, saving, and migration
        - ChangeDetector: Unified change detection with phase parameter
        - cleanup: Deleted file cleanup

    Creation:
        Direct instantiation: IncrementalOrchestrator(site)
            - Created by BuildOrchestrator when incremental builds enabled
            - Requires Site instance with content populated

    Attributes:
        site: Site instance for incremental builds
        cache: BuildCache instance for build state persistence
        tracker: DependencyTracker instance for dependency graph construction
        _cache_manager: CacheManager instance for cache operations
        _change_detector: ChangeDetector instance for change detection (lazy)
        _use_unified_change_detector: Feature flag for new detector
        _shadow_mode: Enable shadow execution for validation

    Configuration:
        Feature flags are read from site.config:
        - use_unified_change_detector: Use new unified ChangeDetector
        - shadow_mode: Run both paths and compare results

    Example:
        >>> orchestrator = IncrementalOrchestrator(site)
        >>> cache, tracker = orchestrator.initialize(enabled=True)
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
        self.tracker: DependencyTracker | None = None
        self.logger = get_logger(__name__)

        # Component instances
        self._cache_manager = CacheManager(site)
        self._change_detector: ChangeDetector | None = None

        # Feature flags (read from config, default to False for safety)
        # Be defensive with config access since site.config may be a Mock in tests
        self._use_unified_change_detector = False
        self._shadow_mode = False

        try:
            config = site.config
            if hasattr(config, "get") and callable(config.get):
                # Dict-like config
                build_config = config.get("build", {})
                if isinstance(build_config, dict):
                    self._use_unified_change_detector = build_config.get(
                        "use_unified_change_detector", False
                    )
                    self._shadow_mode = build_config.get("shadow_mode", False)
            elif isinstance(config, dict):
                build_config = config.get("build", {})
                if isinstance(build_config, dict):
                    self._use_unified_change_detector = build_config.get(
                        "use_unified_change_detector", False
                    )
                    self._shadow_mode = build_config.get("shadow_mode", False)
        except (AttributeError, TypeError):
            # Config is a Mock or doesn't have expected structure, use defaults
            pass

    def initialize(self, enabled: bool = False) -> tuple[BuildCache, DependencyTracker]:
        """
        Initialize cache and dependency tracker for incremental builds.

        Delegates to CacheManager for cache operations.

        Args:
            enabled: Whether incremental builds are enabled

        Returns:
            Tuple of (BuildCache, DependencyTracker) instances
        """
        self.cache, self.tracker = self._cache_manager.initialize(enabled)
        return self.cache, self.tracker

    def check_config_changed(self) -> bool:
        """
        Check if configuration has changed (requires full rebuild).

        Delegates to CacheManager for config validation.

        Returns:
            True if config changed (cache was invalidated)
        """
        # Sync cache state with cache manager
        self._cache_manager.cache = self.cache
        return self._cache_manager.check_config_changed()

    def find_work_early(
        self,
        verbose: bool = False,
        forced_changed_sources: set[Path] | None = None,
        nav_changed_sources: set[Path] | None = None,
    ) -> tuple[list[Page], list[Asset], ChangeSummary]:
        """
        Find pages/assets that need rebuilding (early version - before taxonomy).

        This is called BEFORE taxonomies/menus are generated, so it only checks
        content/asset changes. Generated pages will be determined later.

        If use_unified_change_detector is enabled, uses the new ChangeDetector.
        Otherwise falls back to legacy implementation.

        Args:
            verbose: Whether to collect detailed change information
            forced_changed_sources: Paths explicitly changed (from watcher)
            nav_changed_sources: Paths with navigation-affecting changes

        Returns:
            Tuple of (pages_to_build, assets_to_process, change_summary)
        """
        if not self.cache or not self.tracker:
            raise RuntimeError("Cache not initialized - call initialize() first")

        if self._use_unified_change_detector:
            return self._find_work_early_unified(
                verbose=verbose,
                forced_changed_sources=forced_changed_sources,
                nav_changed_sources=nav_changed_sources,
            )
        else:
            return self._find_work_early_legacy(
                verbose=verbose,
                forced_changed_sources=forced_changed_sources,
                nav_changed_sources=nav_changed_sources,
            )

    def _find_work_early_unified(
        self,
        verbose: bool = False,
        forced_changed_sources: set[Path] | None = None,
        nav_changed_sources: set[Path] | None = None,
    ) -> tuple[list[Page], list[Asset], ChangeSummary]:
        """Find work using unified ChangeDetector."""
        # Lazy initialization of change detector
        if self._change_detector is None:
            self._change_detector = ChangeDetector(self.site, self.cache, self.tracker)

        change_set = self._change_detector.detect_changes(
            phase="early",
            verbose=verbose,
            forced_changed_sources=forced_changed_sources,
            nav_changed_sources=nav_changed_sources,
        )

        if self._shadow_mode:
            # Run legacy path and compare
            legacy_pages, legacy_assets, legacy_summary = self._find_work_early_legacy(
                verbose=verbose,
                forced_changed_sources=forced_changed_sources,
                nav_changed_sources=nav_changed_sources,
            )
            self._compare_results(
                "find_work_early",
                new_pages=change_set.pages_to_build,
                new_assets=change_set.assets_to_process,
                legacy_pages=legacy_pages,
                legacy_assets=legacy_assets,
            )

        return (
            change_set.pages_to_build,
            change_set.assets_to_process,
            change_set.change_summary,
        )

    def _find_work_early_legacy(
        self,
        verbose: bool = False,
        forced_changed_sources: set[Path] | None = None,
        nav_changed_sources: set[Path] | None = None,
    ) -> tuple[list[Page], list[Asset], ChangeSummary]:
        """Legacy implementation of find_work_early."""
        # Import here to avoid circular imports with the new structure
        from bengal.orchestration.incremental.cascade_tracker import CascadeTracker
        from bengal.orchestration.incremental.rebuild_filter import RebuildFilter

        forced_changed = {Path(p) for p in (forced_changed_sources or set())}
        nav_changed = {Path(p) for p in (nav_changed_sources or set())}

        pages_to_rebuild: set[Path] = set()
        assets_to_process: list[Asset] = []
        change_summary = ChangeSummary()

        rebuild_filter = RebuildFilter(self.site, self.cache)
        cascade_tracker = CascadeTracker(self.site)

        # Section-level filtering
        changed_sections = None
        if hasattr(self.site, "sections") and self.site.sections:
            changed_sections = rebuild_filter.get_changed_sections(self.site.sections)

            for forced_path in forced_changed | nav_changed:
                forced_page = next(
                    (p for p in self.site.pages if p.source_path == forced_path), None
                )
                sec = getattr(forced_page, "_section", None)
                if sec:
                    changed_sections.add(sec)

            if verbose and changed_sections:
                logger.debug(
                    "section_level_filtering",
                    total_sections=len(self.site.sections),
                    changed_sections=len(changed_sections),
                )

        pages_to_check = rebuild_filter.select_pages_to_check(
            changed_sections=changed_sections,
            forced_changed=forced_changed,
            nav_changed=nav_changed,
        )

        for page in pages_to_check:
            if page.metadata.get("_generated"):
                continue

            if (
                changed_sections is not None
                and hasattr(page, "_section")
                and page._section
                and page._section not in changed_sections
            ):
                continue

            all_changed = forced_changed | nav_changed
            if self.cache.should_bypass(page.source_path, all_changed):
                pages_to_rebuild.add(page.source_path)
                if verbose:
                    change_summary.modified_content.append(page.source_path)
                if page.tags:
                    self.tracker.track_taxonomy(page.source_path, set(page.tags))

        cascade_affected_count = cascade_tracker.apply_cascade_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            verbose=verbose,
            change_summary=change_summary,
        )

        if cascade_affected_count > 0:
            logger.info(
                "cascade_dependencies_detected",
                additional_pages=cascade_affected_count,
                reason="section_cascade_metadata_changed",
            )

        rebuild_filter.apply_shared_content_cascade(
            pages_to_rebuild=pages_to_rebuild,
            forced_changed=forced_changed,
            verbose=verbose,
            change_summary=change_summary,
        )

        all_changed = forced_changed | nav_changed
        rebuild_filter.apply_nav_frontmatter_section_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            all_changed=all_changed,
            verbose=verbose,
            change_summary=change_summary,
        )

        navigation_affected_count = cascade_tracker.apply_adjacent_navigation_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            verbose=verbose,
            change_summary=change_summary,
        )

        if navigation_affected_count > 0:
            logger.info(
                "navigation_dependencies_detected",
                additional_pages=navigation_affected_count,
                reason="adjacent_pages_have_nav_links_to_modified_pages",
            )

        for asset in self.site.assets:
            if self.cache.should_bypass(asset.source_path, forced_changed):
                assets_to_process.append(asset)
                if verbose:
                    change_summary.modified_assets.append(asset.source_path)

        # Check templates
        theme_templates_dir = self._get_theme_templates_dir()
        if theme_templates_dir and theme_templates_dir.exists():
            for template_file in theme_templates_dir.rglob("*.html"):
                if self.cache.is_changed(template_file):
                    if verbose and template_file not in change_summary.modified_templates:
                        change_summary.modified_templates.append(template_file)
                    affected = self.cache.get_affected_pages(template_file)
                    for page_path_str in affected:
                        pages_to_rebuild.add(Path(page_path_str))
                else:
                    self.cache.update_file(template_file)

        site_templates_dir = self.site.root_path / "templates"
        if site_templates_dir.exists():
            for template_file in site_templates_dir.rglob("*.html"):
                if self.cache.is_changed(template_file):
                    if verbose and template_file not in change_summary.modified_templates:
                        change_summary.modified_templates.append(template_file)
                    affected = self.cache.get_affected_pages(template_file)
                    for page_path_str in affected:
                        pages_to_rebuild.add(Path(page_path_str))
                else:
                    self.cache.update_file(template_file)

        # Check autodoc changes
        import contextlib

        autodoc_pages_to_rebuild: set[str] = set()
        if (
            self.cache
            and hasattr(self.cache, "autodoc_dependencies")
            and hasattr(self.cache, "get_autodoc_source_files")
        ):
            try:

                def _is_external_autodoc_source(path: Path) -> bool:
                    parts = path.parts
                    return (
                        "site-packages" in parts
                        or "dist-packages" in parts
                        or ".venv" in parts
                        or ".tox" in parts
                    )

                source_files = self.cache.get_autodoc_source_files()
                if source_files:
                    for source_file in source_files:
                        source_path = Path(source_file)
                        if _is_external_autodoc_source(source_path):
                            continue
                        if self.cache.is_changed(source_path):
                            affected_pages = self.cache.get_affected_autodoc_pages(source_path)
                            if affected_pages:
                                autodoc_pages_to_rebuild.update(affected_pages)

                                if verbose:
                                    if "Autodoc changes" not in change_summary.extra_changes:
                                        change_summary.extra_changes["Autodoc changes"] = []
                                    msg = f"{source_path.name} changed"
                                    msg += f", affects {len(affected_pages)}"
                                    msg += " autodoc pages"
                                    change_summary.extra_changes["Autodoc changes"].append(msg)

                if autodoc_pages_to_rebuild:
                    logger.info(
                        "autodoc_selective_rebuild",
                        affected_pages=len(autodoc_pages_to_rebuild),
                        reason="source_files_changed",
                    )
            except (TypeError, AttributeError):
                pass

        # Convert to Page objects
        has_autodoc_tracking = False
        if self.cache and hasattr(self.cache, "autodoc_dependencies"):
            with contextlib.suppress(TypeError, AttributeError):
                has_autodoc_tracking = bool(self.cache.autodoc_dependencies)

        pages_to_build_list = [
            page
            for page in self.site.pages
            if (page.source_path in pages_to_rebuild and not page.metadata.get("_generated"))
            or (
                page.metadata.get("is_autodoc")
                and (str(page.source_path) in autodoc_pages_to_rebuild or not has_autodoc_tracking)
            )
        ]

        logger.info(
            "incremental_work_detected",
            pages_to_build=len(pages_to_build_list),
            assets_to_process=len(assets_to_process),
            modified_pages=len(change_summary.modified_content),
            modified_templates=len(change_summary.modified_templates),
            modified_assets=len(change_summary.modified_assets),
            total_pages=len(self.site.pages),
        )

        return pages_to_build_list, assets_to_process, change_summary

    def find_work(
        self, verbose: bool = False
    ) -> tuple[list[Page], list[Asset], dict[str, list[Any]]]:
        """
        Find pages/assets that need rebuilding (legacy version - after taxonomy).

        This is the old method that expects generated pages to already exist.
        Kept for backward compatibility.

        Args:
            verbose: Whether to collect detailed change information

        Returns:
            Tuple of (pages_to_build, assets_to_process, change_summary)
        """
        if not self.cache or not self.tracker:
            raise RuntimeError("Cache not initialized - call initialize() first")

        if self._use_unified_change_detector:
            return self._find_work_unified(verbose=verbose)
        else:
            return self._find_work_legacy(verbose=verbose)

    def _find_work_unified(
        self, verbose: bool = False
    ) -> tuple[list[Page], list[Asset], dict[str, list[Any]]]:
        """Find work using unified ChangeDetector."""
        if self._change_detector is None:
            self._change_detector = ChangeDetector(self.site, self.cache, self.tracker)

        change_set = self._change_detector.detect_changes(
            phase="full",
            verbose=verbose,
        )

        # Convert ChangeSummary to legacy dict format
        summary_dict: dict[str, list[Any]] = {
            "Modified content": list(change_set.change_summary.modified_content),
            "Modified assets": list(change_set.change_summary.modified_assets),
            "Modified templates": list(change_set.change_summary.modified_templates),
            "Taxonomy changes": change_set.change_summary.extra_changes.get("Taxonomy changes", []),
        }

        if self._shadow_mode:
            legacy_pages, legacy_assets, legacy_summary = self._find_work_legacy(verbose=verbose)
            self._compare_results(
                "find_work",
                new_pages=change_set.pages_to_build,
                new_assets=change_set.assets_to_process,
                legacy_pages=legacy_pages,
                legacy_assets=legacy_assets,
            )

        return change_set.pages_to_build, change_set.assets_to_process, summary_dict

    def _find_work_legacy(
        self, verbose: bool = False
    ) -> tuple[list[Page], list[Asset], dict[str, list[Any]]]:
        """Legacy implementation of find_work (full phase)."""
        from bengal.orchestration.incremental.rebuild_filter import RebuildFilter

        pages_to_rebuild: set[Path] = set()
        assets_to_process: list[Asset] = []
        change_summary: dict[str, list[Any]] = {
            "Modified content": [],
            "Modified assets": [],
            "Modified templates": [],
            "Taxonomy changes": [],
        }

        rebuild_filter = RebuildFilter(self.site, self.cache)

        # Section-level filtering
        changed_sections = None
        if hasattr(self.site, "sections") and self.site.sections:
            changed_sections = rebuild_filter.get_changed_sections(self.site.sections)
            if verbose and changed_sections:
                logger.debug(
                    "section_level_filtering",
                    total_sections=len(self.site.sections),
                    changed_sections=len(changed_sections),
                )

        pages_to_check = self.site.pages
        if changed_sections is not None:
            changed_section_paths = {s.path for s in changed_sections}
            pages_to_check = [
                p
                for p in self.site.pages
                if p.metadata.get("_generated")
                or (
                    hasattr(p, "_section")
                    and p._section
                    and p._section.path in changed_section_paths
                )
                or (not hasattr(p, "_section") or p._section is None)
            ]

        for page in pages_to_check:
            if page.metadata.get("_generated"):
                continue

            if (
                changed_sections is not None
                and hasattr(page, "_section")
                and page._section
                and page._section not in changed_sections
            ):
                continue

            if self.cache.is_changed(page.source_path):
                pages_to_rebuild.add(page.source_path)
                if verbose:
                    change_summary["Modified content"].append(page.source_path)
                if page.tags:
                    self.tracker.track_taxonomy(page.source_path, set(page.tags))

        for asset in self.site.assets:
            if self.cache.is_changed(asset.source_path):
                assets_to_process.append(asset)
                if verbose:
                    change_summary["Modified assets"].append(asset.source_path)

        theme_templates_dir = self._get_theme_templates_dir()
        if theme_templates_dir and theme_templates_dir.exists():
            for template_file in theme_templates_dir.rglob("*.html"):
                if self.cache.is_changed(template_file):
                    if verbose:
                        change_summary["Modified templates"].append(template_file)
                    affected = self.cache.get_affected_pages(template_file)
                    for page_path_str in affected:
                        pages_to_rebuild.add(Path(page_path_str))
                else:
                    self.cache.update_file(template_file)

        # Taxonomy handling
        affected_tags: set[str] = set()
        affected_sections = set()

        for page in self.site.regular_pages:
            if page.source_path in pages_to_rebuild:
                old_tags = self.cache.get_previous_tags(page.source_path)
                new_tags = set(page.tags) if page.tags else set()

                added_tags = new_tags - old_tags
                removed_tags = old_tags - new_tags

                for tag in added_tags | removed_tags:
                    affected_tags.add(tag.lower().replace(" ", "-"))
                    if verbose:
                        change_summary["Taxonomy changes"].append(
                            f"Tag '{tag}' changed on {page.source_path.name}"
                        )

                if hasattr(page, "section"):
                    affected_sections.add(page.section)

        if affected_tags:
            for page in self.site.generated_pages:
                if page.metadata.get("type") in ("tag", "tag-index"):
                    tag_slug = page.metadata.get("_tag_slug")
                    if (
                        tag_slug
                        and tag_slug in affected_tags
                        or page.metadata.get("type") == "tag-index"
                    ):
                        pages_to_rebuild.add(page.source_path)

        if affected_sections:
            for page in self.site.pages:
                if page.metadata.get("_generated") and page.metadata.get("type") == "archive":
                    page_section = page.metadata.get("_section")
                    if page_section and page_section in affected_sections:
                        pages_to_rebuild.add(page.source_path)

        # Autodoc handling

        autodoc_pages_to_rebuild: set[str] = set()
        has_autodoc_tracking = False
        if (
            self.cache
            and hasattr(self.cache, "autodoc_dependencies")
            and hasattr(self.cache, "get_autodoc_source_files")
        ):
            try:
                source_files = self.cache.get_autodoc_source_files()
                if source_files:
                    has_autodoc_tracking = bool(self.cache.autodoc_dependencies)
                    for source_file in source_files:
                        source_path = Path(source_file)
                        if self.cache.is_changed(source_path):
                            affected_pages = self.cache.get_affected_autodoc_pages(source_path)
                            if affected_pages:
                                autodoc_pages_to_rebuild.update(affected_pages)
            except (TypeError, AttributeError):
                pass

        pages_to_build = [
            page
            for page in self.site.pages
            if page.source_path in pages_to_rebuild
            or (
                page.metadata.get("is_autodoc")
                and (str(page.source_path) in autodoc_pages_to_rebuild or not has_autodoc_tracking)
            )
        ]

        return pages_to_build, assets_to_process, change_summary

    def _compare_results(
        self,
        method_name: str,
        *,
        new_pages: list[Page],
        new_assets: list[Asset],
        legacy_pages: list[Page],
        legacy_assets: list[Asset],
    ) -> None:
        """Compare results from new and legacy implementations."""
        new_page_paths = {p.source_path for p in new_pages}
        legacy_page_paths = {p.source_path for p in legacy_pages}

        new_asset_paths = {a.source_path for a in new_assets}
        legacy_asset_paths = {a.source_path for a in legacy_assets}

        if new_page_paths != legacy_page_paths:
            only_in_new = new_page_paths - legacy_page_paths
            only_in_legacy = legacy_page_paths - new_page_paths
            logger.warning(
                "shadow_mode_page_mismatch",
                method=method_name,
                only_in_new=len(only_in_new),
                only_in_legacy=len(only_in_legacy),
                only_in_new_paths=[str(p) for p in list(only_in_new)[:5]],
                only_in_legacy_paths=[str(p) for p in list(only_in_legacy)[:5]],
            )
        else:
            logger.debug(
                "shadow_mode_page_match",
                method=method_name,
                page_count=len(new_page_paths),
            )

        if new_asset_paths != legacy_asset_paths:
            only_in_new = new_asset_paths - legacy_asset_paths
            only_in_legacy = legacy_asset_paths - new_asset_paths
            logger.warning(
                "shadow_mode_asset_mismatch",
                method=method_name,
                only_in_new=len(only_in_new),
                only_in_legacy=len(only_in_legacy),
            )
        else:
            logger.debug(
                "shadow_mode_asset_match",
                method=method_name,
                asset_count=len(new_asset_paths),
            )

    def process(self, change_type: str, changed_paths: set[str]) -> None:
        """
        Bridge-style process for testing incremental invalidation.

        ⚠️  TEST BRIDGE ONLY - See docstring for details.
        """
        if not self.tracker:
            raise RuntimeError("Tracker not initialized - call initialize() first")

        import sys

        if "pytest" not in sys.modules:
            logger.warning(
                "IncrementalOrchestrator.process() is a test bridge. "
                "Use run() or full_build() for production builds."
            )

        context = BuildContext(site=self.site, pages=self.site.pages, tracker=self.tracker)

        path_set: set[Path] = {Path(p) for p in changed_paths}
        invalidated: set[Path]
        if change_type == "content":
            invalidated = self.tracker.invalidator.invalidate_content(path_set)
        elif change_type == "template":
            invalidated = self.tracker.invalidator.invalidate_templates(path_set)
        elif change_type == "config":
            invalidated = self.tracker.invalidator.invalidate_config()
        else:
            invalidated = set()

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
        pass

    def _cleanup_deleted_files(self) -> None:
        """Clean up output files for deleted source files."""
        if self.cache:
            cleanup_deleted_files(self.site, self.cache)

    def save_cache(self, pages_built: list[Page], assets_processed: list[Asset]) -> None:
        """
        Update cache with processed files.

        Delegates to CacheManager.

        Args:
            pages_built: Pages that were built
            assets_processed: Assets that were processed
        """
        self._cache_manager.cache = self.cache
        self._cache_manager.save(pages_built, assets_processed)

    def _get_theme_templates_dir(self) -> Path | None:
        """
        Get the templates directory for the current theme.

        Delegates to CacheManager for backwards compatibility.

        Returns:
            Path to theme templates or None if not found
        """
        return self._cache_manager._get_theme_templates_dir()
