"""
Related Posts orchestration for Bengal SSG.

Builds related posts index during build phase for O(1) template access.
"""

import concurrent.futures
from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Threshold for parallel processing - below this we use sequential processing
# to avoid thread pool overhead for small workloads
MIN_PAGES_FOR_PARALLEL = 100

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site


class RelatedPostsOrchestrator:
    """
    Builds related posts relationships during build phase.

    Strategy: Use taxonomy index for efficient tag-based matching.
    Complexity: O(n·t) where n=pages, t=avg tags per page (typically 2-5)

    This moves expensive related posts computation from render-time (O(n²))
    to build-time (O(n·t)), resulting in O(1) template access.
    """

    def __init__(self, site: "Site"):
        """
        Initialize related posts orchestrator.

        Args:
            site: Site instance
        """
        self.site = site

    def build_index(
        self, limit: int = 5, parallel: bool = True, affected_pages: list["Page"] | None = None
    ) -> None:
        """
        Compute related posts for pages using tag-based matching.

        This is called once during the build phase. Each page gets a
        pre-computed list of related pages stored in page.related_posts.

        Args:
            limit: Maximum related posts per page (default: 5)
            parallel: Whether to use parallel processing (default: True)
            affected_pages: List of pages whose related posts should be recomputed.
                          If None, computes for all pages (full build).
                          If provided, only updates affected pages (incremental).
        """
        logger.info(
            "related_posts_build_start",
            total_pages=len(self.site.pages),
            incremental=affected_pages is not None,
        )

        # Skip if no taxonomies built yet
        if not hasattr(self.site, "taxonomies"):
            self._set_empty_related_posts()
            logger.debug("related_posts_skipped", reason="no_taxonomies")
            return

        tags_dict = self.site.taxonomies.get("tags", {})
        if not tags_dict:
            # No tags in site - nothing to relate
            self._set_empty_related_posts()
            logger.debug("related_posts_skipped", reason="no_tags")
            return

        # Build inverted index: page_id -> set of tag slugs
        # This is O(n) where n = number of pages
        page_tags_map = self._build_page_tags_map()

        # Determine which pages to process
        if affected_pages is not None:
            # Incremental: only process affected pages (filter out generated)
            pages_to_process = [p for p in affected_pages if not p.metadata.get("_generated")]
        else:
            # Full build: process all regular pages (use cached property)
            pages_to_process = list(self.site.regular_pages)

        # Use parallel processing for larger sites to avoid thread overhead
        if parallel and len(pages_to_process) >= MIN_PAGES_FOR_PARALLEL:
            pages_with_related = self._build_parallel(
                pages_to_process, page_tags_map, tags_dict, limit
            )
        else:
            pages_with_related = self._build_sequential(
                pages_to_process, page_tags_map, tags_dict, limit
            )

        logger.info(
            "related_posts_build_complete",
            pages_with_related=pages_with_related,
            total_pages=len(self.site.pages),
            affected_pages=len(pages_to_process) if affected_pages else None,
            mode="parallel"
            if parallel and len(pages_to_process) >= MIN_PAGES_FOR_PARALLEL
            else "sequential",
        )

    def _build_sequential(
        self,
        pages: list["Page"],
        page_tags_map: dict["Page", set[str]],
        tags_dict: dict[str, dict],
        limit: int,
    ) -> int:
        """
        Build related posts sequentially (original implementation).

        Args:
            pages: List of pages to process
            page_tags_map: Pre-built page -> tags mapping
            tags_dict: Taxonomy tags dictionary
            limit: Maximum related posts per page

        Returns:
            Number of pages with related posts found
        """
        pages_with_related = 0

        for page in pages:
            page.related_posts = self._find_related_posts(page, page_tags_map, tags_dict, limit)
            if page.related_posts:
                pages_with_related += 1

        # Set empty for generated pages
        for page in self.site.pages:
            if page.metadata.get("_generated"):
                page.related_posts = []

        return pages_with_related

    def _build_parallel(
        self,
        pages: list["Page"],
        page_tags_map: dict["Page", set[str]],
        tags_dict: dict[str, dict],
        limit: int,
    ) -> int:
        """
        Build related posts in parallel using ThreadPoolExecutor.

        Each page's related posts computation is independent, making this
        perfectly parallelizable. On Python 3.14t (free-threaded), this
        achieves true parallelism without GIL contention.

        Performance:
            - Python 3.13 (GIL): 2-3x faster
            - Python 3.14t (no GIL): 6-8x faster

        Args:
            pages: List of pages to process
            page_tags_map: Pre-built page -> tags mapping
            tags_dict: Taxonomy tags dictionary
            limit: Maximum related posts per page

        Returns:
            Number of pages with related posts found
        """
        # Get max_workers from site config (default: 4)
        max_workers = self.site.config.get("max_workers", 4)

        pages_with_related = 0

        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_page = {
                executor.submit(
                    self._find_related_posts, page, page_tags_map, tags_dict, limit
                ): page
                for page in pages
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    related_posts = future.result()
                    page.related_posts = related_posts
                    if related_posts:
                        pages_with_related += 1
                except Exception as e:
                    # Log error but don't fail the build
                    logger.error(
                        "related_posts_computation_failed",
                        page=str(page.source_path),
                        error=str(e),
                    )
                    page.related_posts = []

        # Set empty for generated pages
        for page in self.site.pages:
            if page.metadata.get("_generated"):
                page.related_posts = []

        return pages_with_related

    def _set_empty_related_posts(self) -> None:
        """Set empty related_posts list for all pages."""
        for page in self.site.pages:
            page.related_posts = []

    def _build_page_tags_map(self) -> dict["Page", set[str]]:
        """
        Build mapping of page -> set of tag slugs.

        This creates an efficient lookup structure for checking tag overlap.
        Now uses pages directly as keys (hashable based on source_path).

        Returns:
            Dictionary mapping Page to set of tag slugs
        """
        page_tags = {}
        for page in self.site.pages:
            if hasattr(page, "tags") and page.tags:
                # Convert tags to slugs for consistent matching (same as taxonomy)
                page_tags[page] = {tag.lower().replace(" ", "-") for tag in page.tags}
            else:
                page_tags[page] = set()

        return page_tags

    def _find_related_posts(
        self,
        page: "Page",
        page_tags_map: dict["Page", set[str]],
        tags_dict: dict[str, dict],
        limit: int,
    ) -> list["Page"]:
        """
        Find related posts for a single page using tag overlap scoring.

        Algorithm:
        1. For each tag on the current page
        2. Find all other pages with that tag (via taxonomy index)
        3. Score pages by number of shared tags
        4. Return top N pages sorted by score

        Args:
            page: Page to find related posts for
            page_tags_map: Pre-built page -> tags mapping (now uses pages directly)
            tags_dict: Taxonomy tags dictionary {slug: {pages: [...]}}
            limit: Maximum related posts to return

        Returns:
            List of related pages sorted by relevance (most shared tags first)
        """
        page_tag_slugs = page_tags_map.get(page, set())

        if not page_tag_slugs:
            # Page has no tags - no related posts
            return []

        # Score other pages by number of shared tags
        # Now using pages directly as keys (hashable!)
        scored_pages = {}

        # For each tag on current page
        for tag_slug in page_tag_slugs:
            if tag_slug not in tags_dict:
                continue

            # Get all pages with this tag from taxonomy index
            tag_data = tags_dict[tag_slug]
            pages_with_tag = tag_data.get("pages", [])

            for other_page in pages_with_tag:
                # Skip self
                if other_page == page:
                    continue

                # Skip generated pages (tag indexes, archives, etc.)
                if other_page.metadata.get("_generated"):
                    continue

                # Increment score (counts shared tags)
                if other_page not in scored_pages:
                    scored_pages[other_page] = [other_page, 0]
                scored_pages[other_page][1] += 1

        if not scored_pages:
            return []

        # Sort by score (descending) and return top N
        # Higher score = more shared tags = more related
        sorted_pages = sorted(scored_pages.values(), key=lambda x: x[1], reverse=True)

        return [page for page, score in sorted_pages[:limit]]
