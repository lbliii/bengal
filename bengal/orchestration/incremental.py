"""
Incremental build orchestration for Bengal SSG.

Handles cache management, change detection, and determining what needs rebuilding.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.cache import BuildCache, DependencyTracker
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


class IncrementalOrchestrator:
    """
    Handles incremental build logic.

    Responsibilities:
        - Cache initialization and management
        - Change detection (content, assets, templates)
        - Dependency tracking
        - Taxonomy change detection
        - Determining what needs rebuilding
    """

    def __init__(self, site: "Site"):
        """
        Initialize incremental orchestrator.

        Args:
            site: Site instance for incremental builds
        """
        from bengal.utils.logger import get_logger

        self.site = site
        self.cache: BuildCache | None = None
        self.tracker: DependencyTracker | None = None
        self.logger = get_logger(__name__)

    def initialize(self, enabled: bool = False) -> tuple["BuildCache", "DependencyTracker"]:
        """
        Initialize cache and tracker.

        Args:
            enabled: Whether incremental builds are enabled

        Returns:
            Tuple of (cache, tracker)
        """
        import shutil

        from bengal.cache import BuildCache, DependencyTracker

        # New cache location: .bengal/ directory in project root
        cache_dir = self.site.root_path / ".bengal"
        cache_path = cache_dir / "cache.json"

        if enabled:
            # Only create cache directory if enabled
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Legacy cache location (for migration)
            old_cache_path = self.site.output_dir / ".bengal-cache.json"

            # Migrate old cache if exists and new doesn't
            if old_cache_path.exists() and not cache_path.exists():
                try:
                    shutil.copy2(old_cache_path, cache_path)
                    logger.info(
                        "cache_migrated",
                        from_location=str(old_cache_path),
                        to_location=str(cache_path),
                        action="automatic_migration",
                    )
                except Exception as e:
                    logger.warning(
                        "cache_migration_failed", error=str(e), action="using_fresh_cache"
                    )
            self.cache = BuildCache.load(cache_path)
            cache_exists = cache_path.exists()
            try:
                file_count = len(self.cache.file_hashes)
            except (AttributeError, TypeError):
                file_count = 0
            logger.info(
                "cache_initialized",
                enabled=True,
                cache_loaded=cache_exists,
                cached_files=file_count,
                cache_location=str(cache_path),
            )
        else:
            self.cache = BuildCache()
            logger.debug("cache_initialized", enabled=False)

        self.tracker = DependencyTracker(self.cache)

        return self.cache, self.tracker

    def check_config_changed(self) -> bool:
        """
        Check if config file has changed (requires full rebuild).

        Returns:
            True if config changed
        """
        if not self.cache:
            return False

        config_files = [
            self.site.root_path / "bengal.toml",
            self.site.root_path / "bengal.yaml",
            self.site.root_path / "bengal.yml",
        ]
        config_file = next((f for f in config_files if f.exists()), None)

        if config_file:
            # Check if this is the first time we're seeing the config
            file_key = str(config_file)
            is_new = file_key not in self.cache.file_hashes

            changed = self.cache.is_changed(config_file)
            # Always update config file hash (for next build)
            self.cache.update_file(config_file)

            if changed:
                if is_new:
                    logger.info(
                        "config_not_cached",
                        config_file=config_file.name,
                        reason="first_build_or_cache_cleared",
                    )
                else:
                    logger.info(
                        "config_changed", config_file=config_file.name, reason="content_modified"
                    )

            return changed

        return False

    def find_work_early(
        self, verbose: bool = False
    ) -> tuple[list["Page"], list["Asset"], dict[str, list]]:
        """
        Find pages/assets that need rebuilding (early version - before taxonomy generation).

        This is called BEFORE taxonomies/menus are generated, so it only checks content/asset changes.
        Generated pages (tags, etc.) will be determined later based on affected tags.

        Args:
            verbose: Whether to collect detailed change information

        Returns:
            Tuple of (pages_to_build, assets_to_process, change_summary)
        """
        if not self.cache or not self.tracker:
            raise RuntimeError("Cache not initialized - call initialize() first")

        pages_to_rebuild: set[Path] = set()
        assets_to_process: list[Asset] = []
        change_summary: dict[str, list] = {
            "Modified content": [],
            "Modified assets": [],
            "Modified templates": [],
            "Taxonomy changes": [],
        }

        # Find changed content files (skip generated pages - they don't have real source files)
        for page in self.site.pages:
            # Skip generated pages - they'll be handled separately
            if page.metadata.get("_generated"):
                continue

            if self.cache.is_changed(page.source_path):
                pages_to_rebuild.add(page.source_path)
                if verbose:
                    change_summary["Modified content"].append(page.source_path)
                # Track taxonomy changes
                if page.tags:
                    self.tracker.track_taxonomy(page.source_path, set(page.tags))

        # Check for cascade changes and mark dependent pages for rebuild
        # When a section _index.md with cascade metadata changes, all descendant pages
        # need to be rebuilt because their inherited metadata has changed
        cascade_affected_count = 0
        for changed_path in list(pages_to_rebuild):  # Iterate over snapshot
            # Check if this is a section index page (_index.md or index.md)
            if changed_path.stem in ("_index", "index"):
                # Find the Page object for this changed file
                changed_page = next(
                    (p for p in self.site.pages if p.source_path == changed_path), None
                )
                if changed_page and "cascade" in changed_page.metadata:
                    # This is a section index with cascade - find all affected pages
                    affected_pages = self._find_cascade_affected_pages(changed_page)
                    before_count = len(pages_to_rebuild)
                    pages_to_rebuild.update(affected_pages)
                    after_count = len(pages_to_rebuild)
                    newly_affected = after_count - before_count
                    cascade_affected_count += newly_affected

                    if verbose and newly_affected > 0:
                        if "Cascade changes" not in change_summary:
                            change_summary["Cascade changes"] = []
                        change_summary["Cascade changes"].append(
                            f"{changed_path.name} cascade affects {newly_affected} descendant pages"
                        )

        if cascade_affected_count > 0:
            logger.info(
                "cascade_dependencies_detected",
                additional_pages=cascade_affected_count,
                reason="section_cascade_metadata_changed",
            )

        # Find changed assets
        for asset in self.site.assets:
            if self.cache.is_changed(asset.source_path):
                assets_to_process.append(asset)
                if verbose:
                    change_summary["Modified assets"].append(asset.source_path)

        # Check template/theme directory for changes
        theme_templates_dir = self._get_theme_templates_dir()
        if theme_templates_dir and theme_templates_dir.exists():
            for template_file in theme_templates_dir.rglob("*.html"):
                if self.cache.is_changed(template_file):
                    if verbose:
                        change_summary["Modified templates"].append(template_file)
                    # Template changed - find affected pages
                    affected = self.cache.get_affected_pages(template_file)
                    for page_path_str in affected:
                        pages_to_rebuild.add(Path(page_path_str))
                else:
                    # Template unchanged - still update its hash in cache to avoid re-checking
                    self.cache.update_file(template_file)

        # Convert to Page objects
        pages_to_build_list = [
            page
            for page in self.site.pages
            if page.source_path in pages_to_rebuild and not page.metadata.get("_generated")
        ]

        # Log what changed for debugging
        logger.info(
            "incremental_work_detected",
            pages_to_build=len(pages_to_build_list),
            assets_to_process=len(assets_to_process),
            modified_pages=len(change_summary.get("Modified pages", [])),
            modified_templates=len(change_summary.get("Modified templates", [])),
            modified_assets=len(change_summary.get("Modified assets", [])),
            total_pages=len(self.site.pages),
        )

        return pages_to_build_list, assets_to_process, change_summary

    def find_work(
        self, verbose: bool = False
    ) -> tuple[list["Page"], list["Asset"], dict[str, list]]:
        """
        Find pages/assets that need rebuilding (legacy version - after taxonomy generation).

        This is the old method that expects generated pages to already exist.
        Kept for backward compatibility but should be replaced with find_work_early().

        Args:
            verbose: Whether to collect detailed change information

        Returns:
            Tuple of (pages_to_build, assets_to_process, change_summary)
        """
        if not self.cache or not self.tracker:
            raise RuntimeError("Cache not initialized - call initialize() first")

        pages_to_rebuild: set[Path] = set()
        assets_to_process: list[Asset] = []
        change_summary: dict[str, list] = {
            "Modified content": [],
            "Modified assets": [],
            "Modified templates": [],
            "Taxonomy changes": [],
        }

        # Find changed content files (skip generated pages - they have virtual paths)
        for page in self.site.pages:
            # Skip generated pages - they'll be handled separately
            if page.metadata.get("_generated"):
                continue

            if self.cache.is_changed(page.source_path):
                pages_to_rebuild.add(page.source_path)
                if verbose:
                    change_summary["Modified content"].append(page.source_path)
                # Track taxonomy changes
                if page.tags:
                    self.tracker.track_taxonomy(page.source_path, set(page.tags))

        # Find changed assets
        for asset in self.site.assets:
            if self.cache.is_changed(asset.source_path):
                assets_to_process.append(asset)
                if verbose:
                    change_summary["Modified assets"].append(asset.source_path)

        # Check template/theme directory for changes
        theme_templates_dir = self._get_theme_templates_dir()
        if theme_templates_dir and theme_templates_dir.exists():
            for template_file in theme_templates_dir.rglob("*.html"):
                if self.cache.is_changed(template_file):
                    if verbose:
                        change_summary["Modified templates"].append(template_file)
                    # Template changed - find affected pages
                    affected = self.cache.get_affected_pages(template_file)
                    for page_path_str in affected:
                        pages_to_rebuild.add(Path(page_path_str))
                else:
                    # Template unchanged - still update its hash in cache to avoid re-checking
                    self.cache.update_file(template_file)

        # Check for SPECIFIC taxonomy changes (which exact tags were added/removed)
        # Only rebuild tag pages for tags that actually changed
        affected_tags: set[str] = set()
        affected_sections: set[Section] = set()  # Type-safe with hashable sections

        # OPTIMIZATION: Use site.regular_pages (cached) instead of filtering all pages
        for page in self.site.regular_pages:
            # Check if this page changed
            if page.source_path in pages_to_rebuild:
                # Get old and new tags
                old_tags = self.cache.get_previous_tags(page.source_path)
                new_tags = set(page.tags) if page.tags else set()

                # Find which specific tags changed
                added_tags = new_tags - old_tags
                removed_tags = old_tags - new_tags

                # Track affected tags
                for tag in added_tags | removed_tags:
                    affected_tags.add(tag.lower().replace(" ", "-"))
                    if verbose:
                        change_summary["Taxonomy changes"].append(
                            f"Tag '{tag}' changed on {page.source_path.name}"
                        )

                # Check if page changed sections (affects archive pages)
                # For now, mark section as affected if page changed
                if hasattr(page, "section"):
                    affected_sections.add(page.section)

        # Only rebuild specific tag pages that were affected
        # OPTIMIZATION: Use site.generated_pages (cached) instead of filtering all pages
        if affected_tags:
            for page in self.site.generated_pages:
                if page.metadata.get("type") == "tag" or page.metadata.get("type") == "tag-index":
                    # Rebuild tag pages only for affected tags
                    tag_slug = page.metadata.get("_tag_slug")
                    if (
                        tag_slug
                        and tag_slug in affected_tags
                        or page.metadata.get("type") == "tag-index"
                    ):
                        pages_to_rebuild.add(page.source_path)

        # Rebuild archive pages only for affected sections
        if affected_sections:
            for page in self.site.pages:
                if page.metadata.get("_generated") and page.metadata.get("type") == "archive":
                    page_section = page.metadata.get("_section")
                    if page_section and page_section in affected_sections:
                        pages_to_rebuild.add(page.source_path)

        # Convert page paths back to Page objects
        pages_to_build = [page for page in self.site.pages if page.source_path in pages_to_rebuild]

        return pages_to_build, assets_to_process, change_summary

    def _cleanup_deleted_files(self) -> None:
        """
        Clean up output files for deleted source files.

        Checks cache for source files that no longer exist and deletes
        their corresponding output files. This prevents stale content
        from remaining in the output directory after source deletion.
        """
        if not self.cache or not self.cache.output_sources:
            return

        deleted_count = 0

        # Build set of current source paths from output_sources (not file_hashes)
        # output_sources maps output -> source, so we check if those sources still exist
        deleted_sources = []

        for output_path_str, source_path_str in self.cache.output_sources.items():
            source_path = Path(source_path_str)
            # Check if source file still exists on disk
            if not source_path.exists():
                deleted_sources.append((output_path_str, source_path_str))

        if deleted_sources:
            self.logger.info(
                "deleted_sources_detected",
                count=len(deleted_sources),
                files=[Path(src).name for _, src in deleted_sources[:5]],  # Show first 5
            )

        # Clean up output files for deleted sources
        for output_path_str, source_path_str in deleted_sources:
            # Delete the output file
            output_path = self.site.output_dir / output_path_str
            if output_path.exists():
                try:
                    output_path.unlink()
                    deleted_count += 1
                    self.logger.debug(
                        "deleted_output_file",
                        source=Path(source_path_str).name,
                        output=output_path_str,
                    )

                    # Also try to remove empty parent directories
                    try:
                        if output_path.parent != self.site.output_dir:
                            output_path.parent.rmdir()  # Only removes if empty
                    except OSError:
                        pass  # Directory not empty or other issue, ignore

                except Exception as e:
                    self.logger.warning(
                        "failed_to_delete_output", output=output_path_str, error=str(e)
                    )

            # Remove from cache
            if output_path_str in self.cache.output_sources:
                del self.cache.output_sources[output_path_str]

            # Remove from file_hashes
            if source_path_str in self.cache.file_hashes:
                del self.cache.file_hashes[source_path_str]
            if source_path_str in self.cache.page_tags:
                del self.cache.page_tags[source_path_str]
            if source_path_str in self.cache.parsed_content:
                del self.cache.parsed_content[source_path_str]

        if deleted_count > 0:
            self.logger.info(
                "cleanup_complete",
                deleted_outputs=deleted_count,
                deleted_sources=len(deleted_sources),
            )

    def save_cache(self, pages_built: list["Page"], assets_processed: list["Asset"]) -> None:
        """
        Update cache with processed files.

        Args:
            pages_built: Pages that were built
            assets_processed: Assets that were processed
        """
        if not self.cache:
            return

        # Use same cache location as initialize()
        cache_dir = self.site.root_path / ".bengal"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "cache.json"

        # Update all page hashes and tags (skip generated pages - they have virtual paths)
        for page in pages_built:
            if not page.metadata.get("_generated"):
                self.cache.update_file(page.source_path)
                # Store tags for next build's comparison
                if page.tags:
                    self.cache.update_tags(page.source_path, set(page.tags))
                else:
                    self.cache.update_tags(page.source_path, set())

        # Update all asset hashes
        for asset in assets_processed:
            self.cache.update_file(asset.source_path)

        # Update template hashes (even if not changed, to track them)
        theme_templates_dir = self._get_theme_templates_dir()
        if theme_templates_dir and theme_templates_dir.exists():
            for template_file in theme_templates_dir.rglob("*.html"):
                self.cache.update_file(template_file)

        # Save cache
        self.cache.save(cache_path)

    def _find_cascade_affected_pages(self, index_page: "Page") -> set[Path]:
        """
        Find all pages affected by a cascade change in a section index.

        When a section's _index.md has cascade metadata and is modified,
        all descendant pages inherit those values and need to be rebuilt.

        Args:
            index_page: Section _index.md page with cascade metadata

        Returns:
            Set of page source paths that should be rebuilt due to cascade
        """
        affected = set()

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
                    # This uses Section.regular_pages_recursive which walks the tree
                    for page in section.regular_pages_recursive:
                        # Skip generated pages (they have virtual paths)
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

    def _get_theme_templates_dir(self) -> Path | None:
        """
        Get the templates directory for the current theme.

        Returns:
            Path to theme templates or None if not found
        """
        if not self.site.theme:
            return None

        # Check in site's themes directory first
        site_theme_dir = self.site.root_path / "themes" / self.site.theme / "templates"
        if site_theme_dir.exists():
            return site_theme_dir

        # Check in Bengal's bundled themes
        import bengal

        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / self.site.theme / "templates"
        if bundled_theme_dir.exists():
            return bundled_theme_dir

        return None
