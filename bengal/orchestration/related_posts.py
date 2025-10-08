"""
Related Posts orchestration for Bengal SSG.

Builds related posts index during build phase for O(1) template access.
"""

from typing import TYPE_CHECKING, List, Dict, Set
from collections import defaultdict

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.page import Page


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
        # Skip if no taxonomies built yet
        if not hasattr(self.site, 'taxonomies'):
            self._set_empty_related_posts()
            return
        
        tags_dict = self.site.taxonomies.get('tags', {})
        if not tags_dict:
            # No tags in site - nothing to relate
            self._set_empty_related_posts()
            return
        
        # Build inverted index: page_id -> set of tag slugs
        # This is O(n) where n = number of pages
        page_tags_map = self._build_page_tags_map()
        
        # Compute related posts for each page
        # This is O(n·t·p) where t = avg tags per page, p = avg pages per tag
        # In practice, t and p are small constants, so effectively O(n)
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
    
    def _set_empty_related_posts(self) -> None:
        """Set empty related_posts list for all pages."""
        for page in self.site.pages:
            page.related_posts = []
    
    def _build_page_tags_map(self) -> Dict[int, Set[str]]:
        """
        Build mapping of page ID -> set of tag slugs.
        
        This creates an efficient lookup structure for checking tag overlap.
        
        Returns:
            Dictionary mapping page id() to set of tag slugs
        """
        page_tags = {}
        for page in self.site.pages:
            if hasattr(page, 'tags') and page.tags:
                # Convert tags to slugs for consistent matching (same as taxonomy)
                page_tags[id(page)] = {tag.lower().replace(' ', '-') for tag in page.tags}
            else:
                page_tags[id(page)] = set()
        
        return page_tags
    
    def _find_related_posts(
        self, 
        page: 'Page',
        page_tags_map: Dict[int, Set[str]],
        tags_dict: Dict[str, Dict],
        limit: int
    ) -> List['Page']:
        """
        Find related posts for a single page using tag overlap scoring.
        
        Algorithm:
        1. For each tag on the current page
        2. Find all other pages with that tag (via taxonomy index)
        3. Score pages by number of shared tags
        4. Return top N pages sorted by score
        
        Args:
            page: Page to find related posts for
            page_tags_map: Pre-built page -> tags mapping
            tags_dict: Taxonomy tags dictionary {slug: {pages: [...]}}
            limit: Maximum related posts to return
        
        Returns:
            List of related pages sorted by relevance (most shared tags first)
        """
        page_id = id(page)
        page_tag_slugs = page_tags_map.get(page_id, set())
        
        if not page_tag_slugs:
            # Page has no tags - no related posts
            return []
        
        # Score other pages by number of shared tags
        # Map page_id -> (page_object, score) to avoid hashable issues
        scored_pages = {}
        
        # For each tag on current page
        for tag_slug in page_tag_slugs:
            if tag_slug not in tags_dict:
                continue
            
            # Get all pages with this tag from taxonomy index
            tag_data = tags_dict[tag_slug]
            pages_with_tag = tag_data.get('pages', [])
            
            for other_page in pages_with_tag:
                other_id = id(other_page)
                
                # Skip self
                if other_id == page_id:
                    continue
                
                # Skip generated pages (tag indexes, archives, etc.)
                if other_page.metadata.get('_generated'):
                    continue
                
                # Increment score (counts shared tags)
                if other_id not in scored_pages:
                    scored_pages[other_id] = [other_page, 0]
                scored_pages[other_id][1] += 1
        
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

