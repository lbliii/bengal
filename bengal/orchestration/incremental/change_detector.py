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

Related Modules:
    - bengal.orchestration.incremental.rebuild_filter: Page/asset filtering
    - bengal.orchestration.incremental.cascade_tracker: Cascade dependencies
    - bengal.cache.dependency_tracker: Template dependencies
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from bengal.orchestration.build.results import ChangeSummary
from bengal.orchestration.incremental.cascade_tracker import CascadeTracker
from bengal.orchestration.incremental.rebuild_filter import RebuildFilter
from bengal.utils.logger import get_logger

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
        self._check_pages(
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
        xver_count = self._apply_cross_version_rebuilds(
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
        self._check_assets(
            forced_changed=forced_changed,
            assets_to_process=assets_to_process,
            change_summary=change_summary,
            verbose=verbose,
        )

        # Check templates
        self._check_templates(
            pages_to_rebuild=pages_to_rebuild,
            change_summary=change_summary,
            verbose=verbose,
        )

        # Phase-specific logic
        if phase == "full":
            # Post-taxonomy: Handle tag page rebuilds
            self._check_taxonomy_changes(
                pages_to_rebuild=pages_to_rebuild,
                change_summary=change_summary,
                verbose=verbose,
            )

        # Check autodoc changes
        autodoc_pages = self._check_autodoc_changes(
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
        for forced_path in forced_changed | nav_changed:
            forced_page = next((p for p in self.site.pages if p.source_path == forced_path), None)
            sec = getattr(forced_page, "_section", None)
            if sec:
                changed_sections.add(sec)

        return changed_sections

    def _check_pages(
        self,
        *,
        pages_to_check: list[Page],
        changed_sections: set[Section] | None,
        all_changed: set[Path],
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Check pages for changes."""
        for page in pages_to_check:
            if page.metadata.get("_generated"):
                continue

            # Skip if page is in an unchanged section
            if (
                changed_sections is not None
                and hasattr(page, "_section")
                and page._section
                and page._section not in changed_sections
            ):
                continue

            # Use centralized cache bypass helper
            if self.cache.should_bypass(page.source_path, all_changed):
                pages_to_rebuild.add(page.source_path)
                if verbose:
                    change_summary.modified_content.append(page.source_path)
                if page.tags:
                    self.tracker.track_taxonomy(page.source_path, set(page.tags))

    def _check_assets(
        self,
        *,
        forced_changed: set[Path],
        assets_to_process: list[Asset],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Check assets for changes."""
        for asset in self.site.assets:
            if self.cache.should_bypass(asset.source_path, forced_changed):
                assets_to_process.append(asset)
                if verbose:
                    change_summary.modified_assets.append(asset.source_path)

    def _check_templates(
        self,
        *,
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Check templates for changes."""
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

        # Also check site-level templates
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

    def _check_taxonomy_changes(
        self,
        *,
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> None:
        """Check for taxonomy (tag) changes in full phase."""
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
                        change_summary.extra_changes.setdefault("Taxonomy changes", [])
                        change_summary.extra_changes["Taxonomy changes"].append(
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

    def _check_autodoc_changes(
        self,
        *,
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> set[str]:
        """Check for autodoc source file changes."""
        autodoc_pages_to_rebuild: set[str] = set()

        if not hasattr(self.cache, "autodoc_dependencies") or not hasattr(
            self.cache, "get_autodoc_source_files"
        ):
            return autodoc_pages_to_rebuild

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

        return autodoc_pages_to_rebuild

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
        return self._apply_version_scope_filter(pages)

    def _apply_version_scope_filter(self, pages: list[Page]) -> list[Page]:
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

    def _apply_cross_version_rebuilds(
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
            page = next((p for p in self.site.pages if p.source_path == changed_path), None)
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

    def _get_theme_templates_dir(self) -> Path | None:
        """Get the templates directory for the current theme."""
        # Be defensive: site.theme may be None, a string, or a Mock in tests
        theme = self.site.theme
        if not theme or not isinstance(theme, str):
            return None

        site_theme_dir = self.site.root_path / "themes" / theme / "templates"
        if site_theme_dir.exists():
            return site_theme_dir

        import bengal

        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / theme / "templates"
        if bundled_theme_dir.exists():
            return bundled_theme_dir

        return None
