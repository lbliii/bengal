"""
Related Posts orchestration for Bengal SSG.

Builds related posts index during build phase for O(1) template access.
"""

from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

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
    
    def __init__(self, site: 'Site'):
        """
        Initialize related posts orchestrator.
        
        Args:
            site: Site instance
        """
        self.site = site
    
    def build_index(self, limit: int = 5) -> None:
        """
        Compute related posts for all pages using tag-based matching.
        
        This is called once during the build phase. Each page gets a
        pre-computed list of related pages stored in page.related_posts.
        
        Args:
            limit: Maximum related posts per page (default: 5)
        """
        logger.info("related_posts_build_start", total_pages=len(self.site.pages))
        
        # Skip if no taxonomies built yet
        if not hasattr(self.site, 'taxonomies'):
            self._set_empty_related_posts()
            logger.debug("related_posts_skipped", reason="no_taxonomies")
            return
        
        tags_dict = self.site.taxonomies.get('tags', {})
        if not tags_dict:
            # No tags in site - nothing to relate
            self._set_empty_related_posts()
            logger.debug("related_posts_skipped", reason="no_tags")
            return
        
        # Build inverted index: page_id -> set of tag slugs
        # This is O(n) where n = number of pages
        page_tags_map = self._build_page_tags_map()
        
        # Compute related posts for each page
        # This is O(n·t·p) where t = avg tags per page, p = avg pages per tag
        # In practice, t and p are small constants, so effectively O(n)
        pages_with_related = 0
        for page in self.site.pages:
            if page.metadata.get('_generated'):
                # Skip generated pages (tag pages, archives, etc.)
                page.related_posts = []
                continue
            
            page.related_posts = self._find_related_posts(
                page, 
                page_tags_map, 
                tags_dict, 
                limit
            )
            
            if page.related_posts:
                pages_with_related += 1
        
        logger.info(
            "related_posts_build_complete",
            pages_with_related=pages_with_related,
            total_pages=len(self.site.pages)
        )
    
    def _set_empty_related_posts(self) -> None:
        """Set empty related_posts list for all pages."""
        for page in self.site.pages:
            page.related_posts = []
    
    def _build_page_tags_map(self) -> dict['Page', set[str]]:
        """
        Build mapping of page -> set of tag slugs.
        
        This creates an efficient lookup structure for checking tag overlap.
        Now uses pages directly as keys (hashable based on source_path).
        
        Returns:
            Dictionary mapping Page to set of tag slugs
        """
        page_tags = {}
        for page in self.site.pages:
            if hasattr(page, 'tags') and page.tags:
                # Convert tags to slugs for consistent matching (same as taxonomy)
                page_tags[page] = {tag.lower().replace(' ', '-') for tag in page.tags}
            else:
                page_tags[page] = set()
        
        return page_tags
    
    def _find_related_posts(
        self, 
        page: 'Page',
        page_tags_map: dict['Page', set[str]],
        tags_dict: dict[str, dict],
        limit: int
    ) -> list['Page']:
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
            pages_with_tag = tag_data.get('pages', [])
            
            for other_page in pages_with_tag:
                # Skip self
                if other_page == page:
                    continue
                
                # Skip generated pages (tag indexes, archives, etc.)
                if other_page.metadata.get('_generated'):
                    continue
                
                # Increment score (counts shared tags)
                if other_page not in scored_pages:
                    scored_pages[other_page] = [other_page, 0]
                scored_pages[other_page][1] += 1
        
        if not scored_pages:
            return []
        
        # Sort by score (descending) and return top N
        # Higher score = more shared tags = more related
        sorted_pages = sorted(
            scored_pages.values(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return [page for page, score in sorted_pages[:limit]]

