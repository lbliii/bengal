"""
Page and asset filtering for incremental rebuilds.

Identifies which pages and assets need rebuilding based on file changes,
section-level optimizations, and template dependencies.

Key Concepts:
    - Section-level filtering: Skip entire sections if no files changed
    - Force-changed filtering: Always include explicitly changed files
    - Shared content cascade: Versioned content inherits shared content changes

Related Modules:
    - bengal.cache.build_cache: Build cache for change detection
    - bengal.orchestration.incremental: Incremental build coordination
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.orchestration.build.results import ChangeSummary
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site

logger = get_logger(__name__)


class RebuildFilter:
    """
    Filters pages and assets for rebuilding based on change detection.

    Uses section-level optimization to skip checking individual pages in
    unchanged sections, improving performance for large sites.

    Attributes:
        site: Site instance for page and section access
        cache: BuildCache instance for change detection

    Example:
        >>> filter = RebuildFilter(site, cache)
        >>> pages_to_rebuild = filter.find_changed_pages(
        ...     forced_changed=changed_sources,
        ...     nav_changed=nav_sources,
        ... )
    """

    def __init__(self, site: Site, cache: BuildCache) -> None:
        """
        Initialize rebuild filter.

        Args:
            site: Site instance for page and section access
            cache: BuildCache instance for change detection
        """
        self.site = site
        self.cache = cache

    def get_changed_sections(self, sections: list[Section] | None = None) -> set[Section]:
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

    def select_pages_to_check(
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

        Args:
            changed_sections: Set of sections with changes (None = check all)
            forced_changed: Paths that were explicitly changed (from watcher)
            nav_changed: Paths with navigation-affecting changes

        Returns:
            List of pages to check for changes
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

    def check_shared_content_changes(self, forced_changed: set[Path]) -> bool:
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

    def apply_shared_content_cascade(
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

        Args:
            pages_to_rebuild: Set of page paths to rebuild (modified in place)
            forced_changed: Set of paths known to have changed
            verbose: Whether to collect detailed change information
            change_summary: Summary object to record changes

        Returns:
            Count of pages added due to shared content cascade.
        """
        if not self.check_shared_content_changes(forced_changed):
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

    def apply_nav_frontmatter_section_rebuilds(
        self,
        *,
        pages_to_rebuild: set[Path],
        all_changed: set[Path],
        verbose: bool,
        change_summary: ChangeSummary,
    ) -> int:
        """
        Expand `pages_to_rebuild` when nav-affecting section index frontmatter changes.

        Only triggers section-wide rebuild when nav-affecting keys changed,
        not body-only changes.

        Args:
            pages_to_rebuild: Set of page paths to rebuild (modified in place)
            all_changed: Set of all changed paths (forced + nav)
            verbose: Whether to collect detailed change information
            change_summary: Summary object to record changes

        Returns:
            Count of pages added due to section-wide rebuilds.
        """
        from bengal.orchestration.constants import extract_nav_metadata
        from bengal.utils.hashing import hash_str

        nav_section_affected = 0

        for changed_path in all_changed:
            if changed_path.stem not in ("_index", "index"):
                continue

            section_page = next((p for p in self.site.pages if p.source_path == changed_path), None)
            if not section_page:
                continue

            # Compare only nav-affecting keys between current and cached metadata
            try:
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
