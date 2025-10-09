"""
Taxonomy orchestration for Bengal SSG.

Handles taxonomy collection (tags, categories) and dynamic page generation
(tag pages, archive pages, etc.).
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Set

from bengal.utils.url_strategy import URLStrategy
from bengal.utils.page_initializer import PageInitializer

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.cache.build_cache import BuildCache


class TaxonomyOrchestrator:
    """
    Handles taxonomies and dynamic page generation.
    
    Responsibilities:
        - Collect tags, categories, and other taxonomies
        - Generate tag index pages
        - Generate individual tag pages (with pagination)
    
    Note: Section archive pages are now handled by SectionOrchestrator
    """
    
    def __init__(self, site: 'Site'):
        """
        Initialize taxonomy orchestrator.
        
        Args:
            site: Site instance containing pages and sections
        """
        self.site = site
        self.url_strategy = URLStrategy()
        self.initializer = PageInitializer(site)
    
    def collect_and_generate(self) -> None:
        """
        Collect taxonomies and generate dynamic pages.
        Main entry point called during build.
        """
        self.collect_taxonomies()
        self.generate_dynamic_pages()
    
    def collect_and_generate_incremental(self, changed_pages: List['Page'], cache: 'BuildCache') -> Set[str]:
        """
        Incrementally update taxonomies for changed pages only.
        
        This is much faster than full collection for large sites with few changes.
        Only updates taxonomy data for pages that changed, returning affected tags.
        
        Args:
            changed_pages: List of pages that changed
            cache: Build cache with previous tag data
            
        Returns:
            Set of affected tag slugs (for regenerating tag pages)
        """
        affected_tags = self.collect_taxonomies_incremental(changed_pages, cache)
        
        if affected_tags:
            # Generate pages only for affected tags
            self.generate_dynamic_pages_for_tags(affected_tags)
        
        return affected_tags
    
    def collect_taxonomies(self) -> None:
        """
        Collect taxonomies (tags, categories, etc.) from all pages.
        Organizes pages by their taxonomic terms.
        """
        print("\n🏷️  Taxonomies:")
        
        # Initialize taxonomy structure
        self.site.taxonomies = {'tags': {}, 'categories': {}}
        
        # Collect from all pages
        for page in self.site.pages:
            # Collect tags
            if page.tags:
                for tag in page.tags:
                    tag_key = tag.lower().replace(' ', '-')
                    if tag_key not in self.site.taxonomies['tags']:
                        self.site.taxonomies['tags'][tag_key] = {
                            'name': tag,
                            'slug': tag_key,
                            'pages': []
                        }
                    self.site.taxonomies['tags'][tag_key]['pages'].append(page)
            
            # Collect categories (if present in metadata)
            if 'category' in page.metadata:
                category = page.metadata['category']
                cat_key = category.lower().replace(' ', '-')
                if cat_key not in self.site.taxonomies['categories']:
                    self.site.taxonomies['categories'][cat_key] = {
                        'name': category,
                        'slug': cat_key,
                        'pages': []
                    }
                self.site.taxonomies['categories'][cat_key]['pages'].append(page)
        
        # Sort pages within each taxonomy by date (newest first)
        for taxonomy_type in self.site.taxonomies:
            for term_data in self.site.taxonomies[taxonomy_type].values():
                term_data['pages'].sort(
                    key=lambda p: p.date if p.date else datetime.min,
                    reverse=True
                )
        
        tag_count = len(self.site.taxonomies.get('tags', {}))
        cat_count = len(self.site.taxonomies.get('categories', {}))
        print(f"   └─ Found {tag_count} tags" + (f", {cat_count} categories" if cat_count else "") + " ✓")
    
    def collect_taxonomies_incremental(self, changed_pages: List['Page'], cache: 'BuildCache') -> Set[str]:
        """
        Incrementally update taxonomies for changed pages only.
        
        This is the key optimization: instead of iterating ALL pages to collect tags,
        we only update the taxonomy index for pages that changed. This makes taxonomy
        collection O(changed) instead of O(all).
        
        Algorithm:
        1. Start with previous taxonomy structure (reuse from last build)
        2. For each changed page:
           a. Get old tags from cache
           b. Remove page from old tag entries
           c. Add page to new tag entries
        3. Return set of affected tag slugs (for regenerating tag pages)
        
        Args:
            changed_pages: List of pages that changed (NOT generated pages)
            cache: Build cache with previous tag data
            
        Returns:
            Set of affected tag slugs that need page regeneration
        """
        print("\n🏷️  Taxonomies (incremental):")
        
        # Start with existing taxonomy structure (or initialize if first build)
        if not hasattr(self.site, 'taxonomies') or not self.site.taxonomies:
            # First build or cache miss - do full collection
            print("   ℹ️  No cached taxonomies, doing full collection")
            self.collect_taxonomies()
            # Mark all tags as affected (need to generate all tag pages)
            return set(self.site.taxonomies.get('tags', {}).keys())
        
        affected_tags = set()
        
        # Process each changed page
        for page in changed_pages:
            # Skip generated pages (they don't have real source files)
            if page.metadata.get('_generated'):
                continue
            
            # Get old tags from cache
            old_tags = cache.get_previous_tags(page.source_path)
            new_tags = set(page.tags) if page.tags else set()
            
            # Helper to convert tag to slug
            def to_slug(tag: str) -> str:
                return tag.lower().replace(' ', '-')
            
            old_tag_slugs = {to_slug(tag) for tag in old_tags}
            new_tag_slugs = {to_slug(tag) for tag in new_tags}
            
            # Find which tags were added/removed
            removed_tags = old_tag_slugs - new_tag_slugs
            added_tags = new_tag_slugs - old_tag_slugs
            
            # Remove page from old tags
            for tag_slug in removed_tags:
                if tag_slug in self.site.taxonomies['tags']:
                    tag_data = self.site.taxonomies['tags'][tag_slug]
                    # Remove page from list (compare by source_path, not id)
                    # In incremental builds, pages are reloaded so id() won't match
                    tag_data['pages'] = [p for p in tag_data['pages'] if p.source_path != page.source_path]
                    affected_tags.add(tag_slug)
                    
                    # Remove empty tag entries
                    if not tag_data['pages']:
                        del self.site.taxonomies['tags'][tag_slug]
            
            # Add page to new tags
            for tag_slug in added_tags:
                # Find the original tag name (not slug) from page.tags
                original_tag = next((t for t in page.tags if to_slug(t) == tag_slug), tag_slug)
                
                if tag_slug not in self.site.taxonomies['tags']:
                    # Create new tag entry
                    self.site.taxonomies['tags'][tag_slug] = {
                        'name': original_tag,
                        'slug': tag_slug,
                        'pages': []
                    }
                
                self.site.taxonomies['tags'][tag_slug]['pages'].append(page)
                affected_tags.add(tag_slug)
            
            # For tags that stayed the same, need to update page reference
            # (in case page content/date changed)
            unchanged_tags = old_tag_slugs & new_tag_slugs
            for tag_slug in unchanged_tags:
                if tag_slug in self.site.taxonomies['tags']:
                    tag_data = self.site.taxonomies['tags'][tag_slug]
                    # Update page reference (remove old, add new)
                    # Compare by source_path since page objects are reloaded in incremental builds
                    tag_data['pages'] = [p for p in tag_data['pages'] if p.source_path != page.source_path]
                    tag_data['pages'].append(page)
                    # Mark as affected (page content/date may have changed, affecting sort order)
                    affected_tags.add(tag_slug)
        
        # Re-sort pages within affected tags by date (newest first)
        for tag_slug in affected_tags:
            if tag_slug in self.site.taxonomies['tags']:
                tag_data = self.site.taxonomies['tags'][tag_slug]
                tag_data['pages'].sort(
                    key=lambda p: p.date if p.date else datetime.min,
                    reverse=True
                )
        
        # Handle categories similarly (if needed - keeping it simple for now)
        # Categories are less common, can be added later if needed
        
        tag_count = len(self.site.taxonomies.get('tags', {}))
        print(f"   ├─ Cached: {tag_count} tag(s)")
        print(f"   ├─ Updated: {len(changed_pages)} page(s)")
        print(f"   └─ Affected: {len(affected_tags)} tag(s) ✓")
        
        return affected_tags
    
    def generate_dynamic_pages_for_tags(self, affected_tags: set) -> None:
        """
        Generate dynamic pages only for specific affected tags (incremental optimization).
        
        Args:
            affected_tags: Set of tag slugs that need page regeneration
        """
        generated_count = 0
        
        # Always regenerate tag index (it lists all tags)
        if self.site.taxonomies.get('tags'):
            tag_index = self._create_tag_index_page()
            if tag_index:
                self.site.pages.append(tag_index)
                generated_count += 1
                print(f"   ├─ Tag index:        1")
            
            # Only generate pages for affected tags
            for tag_slug in affected_tags:
                if tag_slug in self.site.taxonomies['tags']:
                    tag_data = self.site.taxonomies['tags'][tag_slug]
                    tag_pages = self._create_tag_pages(tag_slug, tag_data)
                    for page in tag_pages:
                        self.site.pages.append(page)
                        generated_count += 1
            
            if generated_count > 1:
                print(f"   ├─ Tag pages:        {generated_count - 1}")
                print(f"   └─ Total:            {generated_count} ✓")
    
    def generate_dynamic_pages(self) -> None:
        """
        Generate dynamic taxonomy pages (tag pages, etc.) that don't have source files.
        
        Note: Section archive pages are now generated by SectionOrchestrator
        """
        generated_count = 0
        
        # Generate tag pages
        if self.site.taxonomies.get('tags'):
            # Create tag index page
            tag_index = self._create_tag_index_page()
            if tag_index:
                self.site.pages.append(tag_index)
                generated_count += 1
            
            # Create individual tag pages (with pagination)
            for tag_slug, tag_data in self.site.taxonomies['tags'].items():
                tag_pages = self._create_tag_pages(tag_slug, tag_data)
                for page in tag_pages:
                    self.site.pages.append(page)
                    generated_count += 1
        
        # Count types of generated pages
        tag_count = sum(1 for p in self.site.pages if p.metadata.get('_generated') and 'tag' in p.output_path.parts)
        pagination_count = sum(1 for p in self.site.pages if p.metadata.get('_generated') and '/page/' in str(p.output_path))
        
        if tag_count:
            print(f"   ├─ Tag pages:        {tag_count}")
        if pagination_count:
            print(f"   ├─ Pagination:       {pagination_count}")
        if generated_count > 0:
            print(f"   └─ Total:            {generated_count} ✓")
    
    def _create_tag_index_page(self) -> 'Page':
        """
        Create the main tags index page.
        
        Returns:
            Generated tag index page
        """
        from bengal.core.page import Page
        
        # Create virtual path (delegate to utility)
        virtual_path = self.url_strategy.make_virtual_path(self.site, 'tags')
        
        tag_index = Page(
            source_path=virtual_path,
            content="",
            metadata={
                'title': 'All Tags',
                'template': 'tags.html',
                'type': 'tag-index',
                '_generated': True,
                '_virtual': True,
                '_tags': self.site.taxonomies['tags']
            }
        )
        
        # Compute output path using centralized logic
        tag_index.output_path = self.url_strategy.compute_tag_index_output_path(self.site)
        
        # Ensure page is correctly initialized (sets _site, validates)
        self.initializer.ensure_initialized(tag_index)
        
        return tag_index
    
    def _create_tag_pages(self, tag_slug: str, tag_data: Dict[str, Any]) -> List['Page']:
        """
        Create pages for an individual tag (with pagination if needed).
        
        Args:
            tag_slug: URL-safe tag slug
            tag_data: Dictionary containing tag name and pages
            
        Returns:
            List of generated tag pages
        """
        from bengal.core.page import Page
        from bengal.utils.pagination import Paginator
        
        pages_to_create = []
        per_page = self.site.config.get('pagination', {}).get('per_page', 10)
        
        # Create paginator
        paginator = Paginator(tag_data['pages'], per_page=per_page)
        
        # Create a page for each pagination page
        for page_num in range(1, paginator.num_pages + 1):
            # Create virtual path (delegate to utility)
            virtual_path = self.url_strategy.make_virtual_path(
                self.site, 'tags', tag_slug, f"page_{page_num}"
            )
            
            tag_page = Page(
                source_path=virtual_path,
                content="",
                metadata={
                    'title': f"Posts tagged '{tag_data['name']}'",
                    'template': 'tag.html',
                    'type': 'tag',
                    '_generated': True,
                    '_virtual': True,
                    '_tag': tag_data['name'],
                    '_tag_slug': tag_slug,
                    '_posts': tag_data['pages'],
                    '_paginator': paginator,
                    '_page_num': page_num
                }
            )
            
            # Compute output path using centralized logic
            tag_page.output_path = self.url_strategy.compute_tag_output_path(
                tag_slug=tag_slug,
                page_num=page_num,
                site=self.site
            )
            
            # Ensure page is correctly initialized (sets _site, validates)
            self.initializer.ensure_initialized(tag_page)
            
            pages_to_create.append(tag_page)
        
        return pages_to_create

