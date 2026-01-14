"""
Taxonomy and autodoc change detection for incremental builds.

Handles checking for tag changes, autodoc source file changes,
and taxonomy metadata propagation.

RFC: rfc-incremental-build-dependency-gaps (Phase 2)
- Metadata changes on member pages cascade to term pages
- Title/date/summary changes trigger term page rebuild
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.cache import BuildCache, CacheCoordinator, DependencyTracker
    from bengal.core.section import Section
    from bengal.core.site import Site
    from bengal.orchestration.build.results import ChangeSummary

logger = get_logger(__name__)


class TaxonomyChangeDetector:
    """
    Detects changes in taxonomies (tags) and autodoc sources.
    
    Handles:
    - Tag changes on pages (added/removed tags)
    - Metadata changes on member pages (title/date/summary)
    - Autodoc source file changes
    - Archive page rebuilds when sections change
    
    RFC: rfc-incremental-build-dependency-gaps (Phase 2)
    - When a page's listing-relevant metadata changes, term pages
      that list that page need to be rebuilt.
    
    Cache Invalidation:
        Uses CacheCoordinator for unified cache invalidation when available
        (RFC: rfc-cache-invalidation-architecture). Falls back to direct
        cache.invalidate_rendered_output() for backward compatibility.
    """

    def __init__(
        self,
        site: Site,
        cache: BuildCache,
        tracker: DependencyTracker | None = None,
        coordinator: CacheCoordinator | None = None,
    ) -> None:
        """
        Initialize taxonomy change detector.

        Args:
            site: Site instance for content access
            cache: BuildCache for change detection
            tracker: Optional DependencyTracker for reverse taxonomy lookup
            coordinator: Optional CacheCoordinator for unified invalidation
        """
        self.site = site
        self.cache = cache
        self.tracker = tracker
        self.coordinator = coordinator

    def check_taxonomy_changes(
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
                    # Ensure tag is a string (YAML may parse 'null' as None)
                    if tag is not None:
                        affected_tags.add(str(tag).lower().replace(" ", "-"))
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

    def check_metadata_cascades(
        self,
        *,
        pages_to_rebuild: set[Path],
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> int:
        """
        Check for member page metadata changes that cascade to term pages.
        
        RFC: rfc-incremental-build-dependency-gaps (Phase 2)
        
        When a page's listing-relevant metadata (title, date, summary) changes,
        taxonomy term pages that list that page need to be rebuilt so they
        display the updated metadata.
        
        Args:
            pages_to_rebuild: Set of pages already marked for rebuild
            change_summary: ChangeSummary for logging
            verbose: Whether to log detailed information
            
        Returns:
            Number of additional pages added for rebuild
        """
        if not self.tracker:
            return 0

        pages_added = 0
        term_pages_to_add: set[str] = set()

        # Log reverse_dependencies state (safe access for mocked trackers)
        try:
            reverse_dep_count = len(self.tracker.reverse_dependencies) if self.tracker else 0
        except TypeError:
            reverse_dep_count = 0  # Handle mocked tracker

        logger.debug(
            "check_metadata_cascades_start",
            pages_to_rebuild_count=len(pages_to_rebuild),
            reverse_dependencies_count=reverse_dep_count,
        )

        # Check each page being rebuilt for metadata changes
        for page_path in list(pages_to_rebuild):
            # Find the page object
            page = self._get_page_by_path(page_path)
            if not page:
                logger.debug("check_metadata_cascades_skip_no_page", page_path=str(page_path))
                continue

            # Only check pages with tags (they're listed on term pages)
            if not page.tags:
                logger.debug("check_metadata_cascades_skip_no_tags", page_path=str(page_path))
                continue

            # Check if listing-relevant metadata changed
            if self._listing_metadata_changed(page):
                # Find term pages that list this page
                term_keys = self.tracker.get_term_pages_for_member(page_path)
                # Handle mocked tracker returning Mock instead of set
                try:
                    term_keys_set = set(term_keys) if term_keys else set()
                except TypeError:
                    term_keys_set = set()  # Handle mocked tracker
                logger.debug(
                    "check_metadata_cascades_term_keys",
                    page_path=str(page_path),
                    term_keys_found=len(term_keys_set),
                    term_keys=list(term_keys_set)[:5],  # First 5
                )
                term_pages_to_add.update(term_keys_set)

                if verbose and term_keys:
                    logger.debug(
                        "metadata_cascade_triggered",
                        page=str(page_path.name),
                        term_pages=len(term_keys),
                    )

        # Add term pages to rebuild set
        if term_pages_to_add:
            from bengal.cache.coordinator import PageInvalidationReason

            for term_key in term_pages_to_add:
                # Convert term key to page path
                term_page = self._find_term_page_by_key(term_key)
                if term_page and term_page.source_path not in pages_to_rebuild:
                    pages_to_rebuild.add(term_page.source_path)
                    # Invalidate rendered output cache for term page
                    # Use coordinator if available (RFC: rfc-cache-invalidation-architecture)
                    if self.coordinator:
                        self.coordinator.invalidate_page(
                            term_page.source_path,
                            PageInvalidationReason.TAXONOMY_CASCADE,
                            trigger=str(term_key),
                        )
                    else:
                        self.cache.invalidate_rendered_output(term_page.source_path)
                    pages_added += 1

            if verbose:
                if "Metadata cascades" not in change_summary.extra_changes:
                    change_summary.extra_changes["Metadata cascades"] = []
                change_summary.extra_changes["Metadata cascades"].append(
                    f"{pages_added} term pages need rebuild due to member metadata changes"
                )

            logger.info(
                "taxonomy_metadata_cascade",
                term_pages_rebuilt=pages_added,
                reason="member_metadata_changed",
            )

        return pages_added

    def _listing_metadata_changed(self, page: Any) -> bool:
        """
        Check if a page's listing-relevant metadata may have changed.
        
        Conservative approach: If the page is being rebuilt, assume its
        listing-relevant metadata (title, date, summary) may have changed.
        This ensures term pages are always updated when member pages change.
        
        Note: A more precise approach would store a separate listing_metadata_hash
        in the cache, but the conservative approach guarantees correctness with
        minimal rebuild overhead (term pages are cheap to rebuild).
        
        Args:
            page: Page object
            
        Returns:
            True if page is being rebuilt (listing metadata may have changed)
        """
        # Conservative: If the page has changed at all, assume listing metadata
        # may have changed. This ensures correctness.
        # 
        # Future optimization: Store listing_metadata_hash separately and compare.
        return True

    def _hash_listing_metadata(self, metadata: dict[str, Any]) -> str:
        """
        Hash metadata fields that affect taxonomy listing pages.
        
        Only includes fields that appear in term page listings:
        - title: Displayed in listing
        - date: Used for sorting and display
        - summary/description: May be shown in listing
        - tags: Which term pages list this page
        
        Args:
            metadata: Page metadata dict
            
        Returns:
            16-char hex hash of relevant fields
        """
        # Normalize date to string for consistent hashing
        date_val = metadata.get("date")
        if date_val is not None:
            date_str = str(date_val)
        else:
            date_str = ""

        # Only hash fields that affect term page listings
        relevant = {
            "title": metadata.get("title", ""),
            "date": date_str,
            "summary": metadata.get("summary", "") or metadata.get("description", ""),
            "tags": sorted(str(t) for t in (metadata.get("tags") or []) if t is not None),
        }

        content = json.dumps(relevant, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_page_by_path(self, path: Path) -> Any:
        """Get page object by source path."""
        for page in self.site.pages:
            if page.source_path == path:
                return page
        return None

    def _find_term_page_by_key(self, term_key: str) -> Any:
        """
        Find the generated term page for a term key.
        
        During incremental change detection, the actual generated page
        objects may not exist yet (they're created during the build phase).
        So we also create a synthetic page if not found in site.generated_pages.
        
        Args:
            term_key: Key like "_generated/tags/tag:python"
            
        Returns:
            Page object if found, or synthetic page for path tracking
        """
        # Extract tag slug from key
        # term_key format: "_generated/tags/tag:slug"
        if not term_key.startswith("_generated/tags/tag:"):
            return None

        tag_slug = term_key.split("tag:")[-1]

        # First, try to find the actual generated tag page
        for page in self.site.generated_pages:
            if page.metadata.get("type") == "tag":
                if page.metadata.get("_tag_slug") == tag_slug:
                    return page

        # If not found (common during early incremental detection),
        # create a synthetic page object for path tracking.
        # The actual page will be created during the build phase.
        from types import SimpleNamespace
        
        # Build the expected source path for the tag page
        # Match the format used by make_virtual_path():
        # .bengal/generated/tags/{tag_slug}/index.md
        generated_dir = self.site.paths.generated_dir
        source_path = generated_dir / "tags" / tag_slug / "index.md"
        
        # Create minimal page-like object with required attributes
        synthetic_page = SimpleNamespace(
            source_path=source_path,
            metadata={
                "type": "tag",
                "_tag_slug": tag_slug,
                "_generated": True,
            },
        )
        
        return synthetic_page

    def check_autodoc_changes(
        self,
        *,
        change_summary: ChangeSummary,
        verbose: bool,
    ) -> set[str]:
        """
        Check for autodoc source file changes.

        Uses two detection mechanisms:
        1. Standard change detection (mtime-based via is_changed)
        2. Self-validation (hash-based via get_stale_autodoc_sources)

        The self-validation provides defense-in-depth: even if CI cache keys
        are incorrect, Bengal will detect stale autodoc sources and rebuild
        affected pages automatically.

        See: plan/rfc-ci-cache-inputs.md (Phase 4: Self-Validating Cache)
        """
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

            # Method 1: Standard change detection (mtime-based)
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

            # Method 2: Self-validation (hash-based) - defense in depth
            # This catches stale autodoc even when CI cache keys are incorrect
            if hasattr(self.cache, "get_stale_autodoc_sources"):
                stale_sources = self.cache.get_stale_autodoc_sources(self.site.root_path)
                if stale_sources:
                    for source_key in stale_sources:
                        affected_pages = self.cache.get_affected_autodoc_pages(source_key)
                        if affected_pages:
                            autodoc_pages_to_rebuild.update(affected_pages)

                            if verbose:
                                if "Autodoc self-validation" not in change_summary.extra_changes:
                                    change_summary.extra_changes["Autodoc self-validation"] = []
                                source_name = Path(source_key).name
                                msg = f"{source_name} stale (hash mismatch)"
                                msg += f", affects {len(affected_pages)}"
                                msg += " autodoc pages"
                                change_summary.extra_changes["Autodoc self-validation"].append(msg)

                    logger.info(
                        "autodoc_self_validation_detected_stale",
                        stale_count=len(stale_sources),
                        affected_pages=len(autodoc_pages_to_rebuild),
                    )

            if autodoc_pages_to_rebuild:
                logger.info(
                    "autodoc_selective_rebuild",
                    affected_pages=len(autodoc_pages_to_rebuild),
                    reason="source_files_changed",
                )
        except (TypeError, AttributeError):
            pass

        return autodoc_pages_to_rebuild
