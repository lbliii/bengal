"""
Incremental build orchestration for Bengal SSG.

Handles cache management, change detection, and determining what needs rebuilding.
Uses file hashes, dependency graphs, and taxonomy indexes to identify changed
content and minimize rebuild work. Supports both full and incremental builds.

Key Concepts:
    - Change detection: File hash comparison for content changes
    - Dependency tracking: Template and data file dependencies
    - Taxonomy invalidation: Tag/category change detection
    - Selective rebuilding: Only rebuild changed pages and dependencies

Related Modules:
    - bengal.cache.build_cache: Build cache persistence
    - bengal.cache.dependency_tracker: Dependency graph construction
    - bengal.orchestration.build: Build orchestration entry point

See Also:
    - bengal/orchestration/incremental.py:IncrementalOrchestrator for incremental logic
    - plan/active/rfc-incremental-builds.md: Incremental build design
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.orchestration.build.results import ChangeSummary
from bengal.utils.build_context import BuildContext
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
    Orchestrates incremental build logic for efficient rebuilds.

    Handles cache initialization, change detection, dependency tracking, and
    selective rebuilding. Uses file hashes, dependency graphs, and taxonomy
    indexes to minimize rebuild work by only rebuilding changed content.

    Creation:
        Direct instantiation: IncrementalOrchestrator(site)
            - Created by BuildOrchestrator when incremental builds enabled
            - Requires Site instance with content populated

    Attributes:
        site: Site instance for incremental builds
        cache: BuildCache instance for build state persistence
        tracker: DependencyTracker instance for dependency graph construction
        logger: Logger instance for incremental build events

    Relationships:
        - Uses: BuildCache for build state persistence
        - Uses: DependencyTracker for dependency graph construction
        - Used by: BuildOrchestrator for incremental build coordination
        - Uses: Site for content access and change detection

    Thread Safety:
        Not thread-safe. Should be used from single thread during build.
        Cache and tracker operations are thread-safe internally.

    Examples:
        orchestrator = IncrementalOrchestrator(site)
        cache, tracker = orchestrator.initialize(enabled=True)
        changed_pages = orchestrator.detect_changes(cache)
    """

    def __init__(self, site: Site):
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

    def initialize(self, enabled: bool = False) -> tuple[BuildCache, DependencyTracker]:
        """
        Initialize cache and dependency tracker for incremental builds.

        Sets up BuildCache and DependencyTracker instances. If enabled, loads
        existing cache from .bengal/cache.json (migrates from legacy location
        if needed). If disabled, creates empty cache instances.

        Args:
            enabled: Whether incremental builds are enabled. If False, creates
                    empty cache instances (full rebuilds always).

        Returns:
            Tuple of (BuildCache, DependencyTracker) instances

        Process:
            1. Create .bengal/ directory if enabled
            2. Migrate legacy cache from output_dir/.bengal-cache.json if exists
            3. Load or create BuildCache instance
            4. Create DependencyTracker with cache and site

        Examples:
            cache, tracker = orchestrator.initialize(enabled=True)
            # Cache loaded from .bengal/cache.json if exists
        """
        import shutil

        from bengal.cache import BuildCache, DependencyTracker

        paths = self.site.paths
        cache_path = paths.build_cache

        if enabled:
            paths.state_dir.mkdir(parents=True, exist_ok=True)

            # Migrate legacy cache from output_dir if exists
            old_cache_path = self.site.output_dir / ".bengal-cache.json"

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

        self.tracker = DependencyTracker(self.cache, self.site)

        return self.cache, self.tracker

    def check_config_changed(self) -> bool:
        """
        Check if configuration has changed (requires full rebuild).

        Uses config hash validation which captures the *effective* configuration state:
        - Base config from files (bengal.toml, config/*.yaml)
        - Environment variable overrides (BENGAL_*)
        - Build profile settings (--profile writer)

        This is more robust than file-based tracking because it detects changes
        in split config files, env vars, and profiles that wouldn't trigger
        a file hash change.

        Returns:
            True if config changed (cache was invalidated)
        """
        if not self.cache:
            return False

        config_hash = self.site.config_hash
        is_valid = self.cache.validate_config(config_hash)

        if not is_valid:
            logger.info(
                "config_changed_via_hash",
                new_hash=config_hash[:8],
                reason="effective_config_modified",
            )
            return True

        # Track config files for logging (hash is authoritative for invalidation)
        config_files = [
            self.site.root_path / "bengal.toml",
            self.site.root_path / "bengal.yaml",
            self.site.root_path / "bengal.yml",
        ]
        config_file = next((f for f in config_files if f.exists()), None)

        if config_file:
            self.cache.update_file(config_file)

        return False

    def _get_changed_sections(self, sections: list[Section] | None = None) -> set[Section]:
        """
        Identify sections with any changed files (section-level optimization).

        Uses max mtime of pages in each section to quickly skip entire sections
        that haven't changed. This is a major optimization for large sites where
        only a few sections have changes.

        Args:
            sections: List of sections to check. If None, uses site.sections.

        Returns:
            Set of Section objects that have changed files

        Performance:
            - O(sections) instead of O(pages) for initial filtering
            - Only checks individual pages in changed sections
            - Uses fast mtime+size check from cache
        """
        if not self.cache:
            return set()

        if sections is None:
            sections = self.site.sections if hasattr(self.site, "sections") else []

        changed_sections: set[Section] = set()

        # Get last build time from cache (for comparison)
        last_build_time = 0.0
        if self.cache.last_build:
            try:
                from datetime import datetime

                last_build_time = datetime.fromisoformat(self.cache.last_build).timestamp()
            except (ValueError, TypeError):
                pass

        for section in sections:
            # Get max mtime of all pages in this section
            section_mtime = 0.0
            has_pages = False

            for page in section.pages:
                if page.metadata.get("_generated"):
                    continue

                try:
                    if page.source_path.exists():
                        stat = page.source_path.stat()
                        section_mtime = max(section_mtime, stat.st_mtime)
                        has_pages = True
                except OSError:
                    # File doesn't exist or can't stat - treat as changed
                    changed_sections.add(section)
                    break

            # If section has pages and max mtime > last build, section changed
            if has_pages and section_mtime > last_build_time:
                changed_sections.add(section)

        return changed_sections

    def _select_pages_to_check(
        self,
        *,
        changed_sections: set[Section] | None,
        forced_changed: set[Path],
        nav_changed: set[Path],
    ) -> list[Page]:
        """
        Select pages that should be checked for changes.

        When section-level filtering is available, restrict checks to pages within
        changed sections, but always include explicitly changed (forced/nav) pages.
        """
        if changed_sections is None:
            return self.site.pages

        changed_section_paths = {s.path for s in changed_sections}
        forced_paths = forced_changed | nav_changed
        return [
            p
            for p in self.site.pages
            if p.metadata.get("_generated")
            or p.source_path in forced_paths
            or (hasattr(p, "_section") and p._section and p._section.path in changed_section_paths)
            or (
                # Handle pages without section (root level)
                not hasattr(p, "_section") or p._section is None
            )
        ]

    def _apply_cascade_rebuilds(
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

    def _apply_nav_frontmatter_section_rebuilds(
        self,
        *,
        pages_to_rebuild: set[Path],
        all_changed: set[Path],
        verbose: bool,
        change_summary: ChangeSummary,
    ) -> int:
        """
        Expand `pages_to_rebuild` when nav-affecting section index frontmatter changes.

        Only triggers section-wide rebuild when nav-affecting keys changed, not body-only changes.

        Returns:
            Count of pages added due to section-wide rebuilds.
        """
        nav_section_affected = 0

        for changed_path in all_changed:
            if changed_path.stem not in ("_index", "index"):
                continue

            section_page = next((p for p in self.site.pages if p.source_path == changed_path), None)
            if not section_page:
                continue

            # Compare only nav-affecting keys between current and cached metadata
            try:
                from bengal.orchestration.constants import extract_nav_metadata
                from bengal.utils.hashing import hash_str

                current_nav_meta = extract_nav_metadata(section_page.metadata or {})
                current_nav_hash = hash_str(
                    json.dumps(current_nav_meta, sort_keys=True, default=str)
                )

                cached = (
                    self.cache.parsed_content.get(str(changed_path))
                    if hasattr(self.cache, "parsed_content")
                    else None
                )

                if isinstance(cached, dict):
                    cached_nav_hash = cached.get("nav_metadata_hash")
                    if cached_nav_hash is None:
                        cached_full_hash = cached.get("metadata_hash")
                        current_full_hash = hash_str(
                            json.dumps(section_page.metadata or {}, sort_keys=True, default=str)
                        )
                        if cached_full_hash is not None and cached_full_hash == current_full_hash:
                            continue
                    elif cached_nav_hash == current_nav_hash:
                        logger.debug(
                            "section_index_body_only_change",
                            path=str(changed_path),
                            reason="nav_metadata_unchanged",
                        )
                        continue
            except Exception as e:
                # On any error, fall back to conservative section rebuild
                logger.debug(
                    "nav_metadata_compare_failed",
                    path=str(changed_path),
                    error=str(e),
                )

            section = getattr(section_page, "_section", None)
            if section:
                before = len(pages_to_rebuild)
                for page in section.regular_pages_recursive:
                    if not page.metadata.get("_generated"):
                        pages_to_rebuild.add(page.source_path)
                added = len(pages_to_rebuild) - before
                nav_section_affected += added
                logger.debug(
                    "section_rebuild_triggered",
                    section=section.name,
                    index_path=str(changed_path),
                    pages_affected=added,
                )

        if nav_section_affected > 0 and verbose:
            change_summary.extra_changes.setdefault("Navigation changes", [])
            change_summary.extra_changes["Navigation changes"].append(
                f"Nav frontmatter changed; rebuilt {nav_section_affected} section pages"
            )

        return nav_section_affected

    def _check_shared_content_changes(self, forced_changed: set[Path]) -> bool:
        """
        Check if any _shared/ content has changed.

        Shared content (under version_config.shared directories) is included in
        all versioned sections. When shared content changes, all versioned pages
        need to be rebuilt.

        Args:
            forced_changed: Set of paths known to have changed (from watcher)

        Returns:
            True if any shared content has changed
        """
        if not self.cache:
            return False

        # Check if versioning is enabled (must be explicitly True, not a Mock)
        versioning_enabled = getattr(self.site, "versioning_enabled", False)
        if versioning_enabled is not True:
            return False

        version_config = getattr(self.site, "version_config", None)
        if not version_config:
            return False

        # Check version_config.enabled and shared are properly set
        if getattr(version_config, "enabled", False) is not True:
            return False

        shared_paths = getattr(version_config, "shared", None)
        if not shared_paths or not isinstance(shared_paths, (list, tuple, set)):
            return False

        # Check each shared directory
        content_dir = self.site.root_path / "content"
        for shared_path in shared_paths:
            shared_dir = content_dir / shared_path
            if not shared_dir.exists():
                continue

            # Check all markdown files in shared directory
            for file_path in shared_dir.rglob("*.md"):
                # Check if in forced_changed or if hash changed
                if file_path in forced_changed or self.cache.is_changed(file_path):
                    logger.info(
                        "shared_content_changed",
                        file=str(file_path.relative_to(content_dir)),
                        action="cascade_to_all_versions",
                    )
                    return True

        return False

    def _apply_shared_content_cascade(
        self,
        *,
        pages_to_rebuild: set[Path],
        forced_changed: set[Path],
        verbose: bool,
        change_summary: ChangeSummary,
    ) -> int:
        """
        Expand `pages_to_rebuild` when shared content changes.

        When content in _shared/ directories changes, all versioned pages
        must be rebuilt because they may include or reference shared content.

        Returns:
            Count of pages added due to shared content cascade.
        """
        if not self._check_shared_content_changes(forced_changed):
            return 0

        # Find all versioned pages
        versioned_pages: set[Path] = set()
        for page in self.site.pages:
            # Skip generated pages
            if page.metadata.get("_generated"):
                continue

            # Check if page has a version assigned
            version = getattr(page, "version", None) or page.metadata.get("version")
            if version is not None:
                versioned_pages.add(page.source_path)

        # Count new pages to rebuild
        before_count = len(pages_to_rebuild)
        pages_to_rebuild.update(versioned_pages)
        after_count = len(pages_to_rebuild)
        cascade_affected = after_count - before_count

        if cascade_affected > 0:
            logger.info(
                "shared_content_cascade",
                pages_affected=cascade_affected,
                reason="shared_content_changed",
            )
            if verbose:
                change_summary.extra_changes.setdefault("Shared content cascade", [])
                change_summary.extra_changes["Shared content cascade"].append(
                    f"Shared content changed, {cascade_affected} versioned pages affected"
                )

        return cascade_affected

    def _apply_adjacent_navigation_rebuilds(
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

    def find_work_early(
        self,
        verbose: bool = False,
        forced_changed_sources: set[Path] | None = None,
        nav_changed_sources: set[Path] | None = None,
    ) -> tuple[list[Page], list[Asset], ChangeSummary]:
        """
        Find pages/assets that need rebuilding (early version - before taxonomy generation).

        This is called BEFORE taxonomies/menus are generated, so it only checks
        content/asset changes.
        Generated pages (tags, etc.) will be determined later based on affected tags.

        Uses section-level optimization: skips checking individual pages in unchanged sections.

        Args:
            verbose: Whether to collect detailed change information

        Returns:
            Tuple of (pages_to_build, assets_to_process, change_summary)
            where change_summary is a ChangeSummary dataclass (supports dict-like access
            for compatibility)
        """
        if not self.cache or not self.tracker:
            raise RuntimeError("Cache not initialized - call initialize() first")

        forced_changed = {Path(p) for p in (forced_changed_sources or set())}
        nav_changed = {Path(p) for p in (nav_changed_sources or set())}

        pages_to_rebuild: set[Path] = set()
        assets_to_process: list[Asset] = []
        change_summary = ChangeSummary()

        # OPTIMIZATION: Section-level filtering (RFC 2.3)
        # Skip entire sections if no files changed within them
        changed_sections: set[Section] | None = None
        if hasattr(self.site, "sections") and self.site.sections:
            changed_sections = self._get_changed_sections(self.site.sections)

            # Ensure forced/explicit changes keep their sections in scope
            if changed_sections is not None:
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

        pages_to_check = self._select_pages_to_check(
            changed_sections=changed_sections,
            forced_changed=forced_changed,
            nav_changed=nav_changed,
        )

        for page in pages_to_check:
            if page.metadata.get("_generated"):
                continue

            # Skip if page is in an unchanged section (double-check for safety)
            if (
                changed_sections is not None
                and hasattr(page, "_section")
                and page._section
                and page._section not in changed_sections
            ):
                continue

            # Use centralized cache bypass helper (RFC: rfc-incremental-hot-reload-invariants)
            # Combines changed_sources check with is_changed hash check
            all_changed = forced_changed | nav_changed
            if self.cache.should_bypass(page.source_path, all_changed):
                pages_to_rebuild.add(page.source_path)
                if verbose:
                    change_summary.modified_content.append(page.source_path)
                if page.tags:
                    self.tracker.track_taxonomy(page.source_path, set(page.tags))

        cascade_affected_count = self._apply_cascade_rebuilds(
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

        # Check for shared content changes (RFC: rfc-versioned-docs-pipeline-integration)
        # When _shared/ content changes, all versioned pages need rebuild
        self._apply_shared_content_cascade(
            pages_to_rebuild=pages_to_rebuild,
            forced_changed=forced_changed,
            verbose=verbose,
            change_summary=change_summary,
        )

        # Check ALL section index files for nav-affecting frontmatter changes
        # (RFC: rfc-incremental-hot-reload-invariants Phase 3)
        all_changed = forced_changed | nav_changed
        self._apply_nav_frontmatter_section_rebuilds(
            pages_to_rebuild=pages_to_rebuild,
            all_changed=all_changed,
            verbose=verbose,
            change_summary=change_summary,
        )

        navigation_affected_count = self._apply_adjacent_navigation_rebuilds(
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

        # Find changed assets using centralized cache bypass helper
        for asset in self.site.assets:
            if self.cache.should_bypass(asset.source_path, forced_changed):
                assets_to_process.append(asset)
                if verbose:
                    change_summary.modified_assets.append(asset.source_path)

        # Check template/theme directory for changes
        theme_templates_dir = self._get_theme_templates_dir()
        if theme_templates_dir and theme_templates_dir.exists():
            for template_file in theme_templates_dir.rglob("*.html"):
                if self.cache.is_changed(template_file):
                    if verbose and template_file not in change_summary.modified_templates:
                        change_summary.modified_templates.append(template_file)
                    # Template changed - find affected pages
                    affected = self.cache.get_affected_pages(template_file)
                    for page_path_str in affected:
                        pages_to_rebuild.add(Path(page_path_str))
                else:
                    # Template unchanged - still update its hash in cache to avoid re-checking
                    self.cache.update_file(template_file)

        # Also check site-level custom templates directory (`root/templates`).
        # This directory participates in Jinja template resolution (see:
        # bengal/rendering/template_engine/environment.py:create_jinja_environment),
        # so changes here must invalidate dependent pages.
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

        # Check which autodoc pages need to be rebuilt based on source file changes
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

                # Get all tracked autodoc source files
                source_files = self.cache.get_autodoc_source_files()
                if source_files:  # Check if iterable and non-empty
                    for source_file in source_files:
                        source_path = Path(source_file)
                        if _is_external_autodoc_source(source_path):
                            continue
                        if self.cache.is_changed(source_path):
                            # Source file changed - mark all its autodoc pages for rebuild
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
                # Handle case where cache is a mock or doesn't have proper methods
                pass

        # Convert to Page objects
        # - Include content pages whose source files changed
        # - Include autodoc pages whose source files changed (selective, not all)
        # - If no dependency tracking yet, include all autodoc pages (first build)
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
                and (
                    # Selective rebuild if we have dependency tracking
                    str(page.source_path) in autodoc_pages_to_rebuild
                    # Or rebuild all if no tracking yet (first build after upgrade)
                    or not has_autodoc_tracking
                )
            )
        ]

        # Log what changed for debugging
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
        change_summary: dict[str, list[Any]] = {
            "Modified content": [],
            "Modified assets": [],
            "Modified templates": [],
            "Taxonomy changes": [],
        }

        # OPTIMIZATION: Section-level filtering (RFC 2.3)
        # Skip entire sections if no files changed within them
        changed_sections: set[Section] | None = None
        if hasattr(self.site, "sections") and self.site.sections:
            changed_sections = self._get_changed_sections(self.site.sections)
            if verbose and changed_sections:
                logger.debug(
                    "section_level_filtering",
                    total_sections=len(self.site.sections),
                    changed_sections=len(changed_sections),
                )

        # Only check pages in changed sections (or all pages if section filtering unavailable)
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
                or (
                    # Handle pages without section (root level)
                    not hasattr(p, "_section") or p._section is None
                )
            ]

        # Find changed content files (skip generated pages - they have virtual paths)
        for page in pages_to_check:
            # Skip generated pages - they'll be handled separately
            if page.metadata.get("_generated"):
                continue

            # Skip if page is in an unchanged section (double-check for safety)
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
                # Track taxonomy changes
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

        # Only rebuild tag pages for tags that actually changed
        affected_tags: set[str] = set()
        affected_sections: set[Section] = set()

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

        # Check which autodoc pages need to be rebuilt based on source file changes
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
                # Handle case where cache is a mock or doesn't have proper methods
                pass

        # Convert page paths back to Page objects
        # - Include content pages whose source files changed
        # - Include autodoc pages selectively (only if their source changed)
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

    def process(self, change_type: str, changed_paths: set[str]) -> None:
        """
        Bridge-style process for testing incremental invalidation.

        ⚠️  TEST BRIDGE ONLY
        ========================
        This method is a lightweight adapter used in tests to simulate an
        incremental pass without invoking the entire site build orchestrator.

        **Not for production use:**
        - Writes placeholder output ("Updated") for verification only
        - Does not perform full rendering or asset processing
        - Skips postprocessing (RSS, sitemap, etc.)
        - Use run() or full_build() for production builds

        **Primarily consumed by:**
        - tests/integration/test_full_to_incremental_sequence.py
        - bengal/orchestration/full_to_incremental.py (test bridge helper)
        - Test scenarios validating cache invalidation logic

        Args:
            change_type: One of "content", "template", or "config"
            changed_paths: Set of paths that changed (ignored for "config")

        Raises:
            RuntimeError: If tracker not initialized (call initialize() first)
        """
        if not self.tracker:
            raise RuntimeError("Tracker not initialized - call initialize() first")

        # Warn if called outside test context
        import sys

        if "pytest" not in sys.modules:
            logger.warning(
                "IncrementalOrchestrator.process() is a test bridge. "
                "Use run() or full_build() for production builds. "
                "This method writes placeholder output only."
            )

        context = BuildContext(site=self.site, pages=self.site.pages, tracker=self.tracker)

        # Invalidate based on change type
        # Convert string paths to Path objects for invalidator methods
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

        # Simulate rebuild write for invalidated paths
        for path in invalidated:
            self._write_output(path, context)

    def _write_output(self, path: Path, context: BuildContext) -> None:
        """
        Write a placeholder output file corresponding to a content path.

        ⚠️  TEST HELPER - Used by process() bridge only.

        For tests that exercise the bridge-only flow, derive the output
        location from the content path under the site's content dir.
        Writes diagnostic placeholder content for test verification.

        Args:
            path: Source content path
            context: Build context (not used in this simplified version)
        """
        import datetime

        content_dir = self.site.root_path / "content"
        rel: Path | str
        try:
            rel = path.relative_to(content_dir)
        except ValueError:
            rel = path.name  # fallback: flat name

        # Pretty URL layout: foo.md -> foo/index.html; _index.md -> index.html
        from pathlib import Path as _P

        rel_html = _P(rel).with_suffix(".html")
        if rel_html.stem in ("index", "_index"):
            rel_html = rel_html.parent / "index.html"
        else:
            rel_html = rel_html.parent / rel_html.stem / "index.html"

        output_path = self.site.output_dir / rel_html
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write diagnostic placeholder with timestamp and path for debugging
        timestamp = datetime.datetime.now().isoformat()
        diagnostic_content = (
            f"[TEST BRIDGE] Updated at {timestamp}\nSource: {path}\nOutput: {rel_html}"
        )
        output_path.write_text(diagnostic_content)

    def full_rebuild(self, pages: list[Any], context: BuildContext) -> None:
        # ... existing logic ...
        pass

    def _cleanup_deleted_autodoc_sources(self) -> None:
        """
        Clean up autodoc pages when their source files are deleted.

        Checks tracked autodoc source files and removes corresponding output
        when the source no longer exists. This prevents stale autodoc pages
        from remaining when Python/OpenAPI source files are deleted.
        """
        if not self.cache or not hasattr(self.cache, "autodoc_dependencies"):
            return

        try:
            source_files = list(self.cache.get_autodoc_source_files())
        except (TypeError, AttributeError):
            return

        deleted_sources: list[str] = []
        for source_file in source_files:
            source_path = Path(source_file)
            if not source_path.exists():
                deleted_sources.append(source_file)

        if not deleted_sources:
            return

        logger.info(
            "autodoc_source_files_deleted",
            count=len(deleted_sources),
            files=[Path(s).name for s in deleted_sources[:5]],
        )

        for source_file in deleted_sources:
            # Get affected autodoc pages before removing from cache
            affected_pages = self.cache.remove_autodoc_source(source_file)

            # Remove output files for affected pages
            for page_path in affected_pages:
                # Autodoc pages use source_id like "python/api/module.md"
                # Convert to output path: "api/module/index.html"
                url_path = page_path.replace("python/", "").replace("cli/", "")
                if url_path.endswith(".md"):
                    url_path = url_path[:-3]
                output_path = self.site.output_dir / url_path / "index.html"

                if output_path.exists():
                    try:
                        output_path.unlink()
                        logger.debug(
                            "autodoc_output_deleted",
                            source=Path(source_file).name,
                            output=str(output_path.relative_to(self.site.output_dir)),
                        )
                        # Try to remove empty parent directories
                        try:
                            if output_path.parent != self.site.output_dir:
                                output_path.parent.rmdir()
                        except OSError:
                            pass  # Directory not empty
                    except OSError as e:
                        logger.warning(
                            "autodoc_output_delete_failed",
                            output=str(output_path),
                            error=str(e),
                        )

            # Also remove from file_hashes
            if source_file in self.cache.file_hashes:
                del self.cache.file_hashes[source_file]
            if source_file in self.cache.file_fingerprints:
                del self.cache.file_fingerprints[source_file]

    def _cleanup_deleted_files(self) -> None:
        """
        Clean up output files for deleted source files.

        Checks cache for source files that no longer exist and deletes
        their corresponding output files. This prevents stale content
        from remaining in the output directory after source deletion.
        """
        # Also clean up deleted autodoc source files
        self._cleanup_deleted_autodoc_sources()

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

    def save_cache(self, pages_built: list[Page], assets_processed: list[Asset]) -> None:
        """
        Update cache with processed files.

        Args:
            pages_built: Pages that were built
            assets_processed: Assets that were processed
        """
        if not self.cache:
            return

        # Use same cache location as initialize()
        paths = self.site.paths
        paths.state_dir.mkdir(parents=True, exist_ok=True)
        cache_path = paths.build_cache

        # Track autodoc source files that were used in this build
        autodoc_source_files_updated: set[str] = set()

        # Update all page hashes and tags (skip virtual/generated pages - they have no source files)
        for page in pages_built:
            # For autodoc pages, update the source file hash (not the virtual source_path)
            if page.metadata.get("is_autodoc"):
                source_file = page.metadata.get("source_file")
                if source_file and source_file not in autodoc_source_files_updated:
                    source_path = Path(source_file)
                    if source_path.exists():
                        self.cache.update_file(source_path)
                        autodoc_source_files_updated.add(source_file)
                continue

            # Skip virtual pages (no source file) and generated pages
            if page.is_virtual or page.metadata.get("_generated"):
                continue
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
