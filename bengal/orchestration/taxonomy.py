"""
Taxonomy orchestration for Bengal SSG.

Handles taxonomy collection (tags, categories) and dynamic page generation
(tag pages, archive pages, etc.).
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from bengal.utils.url_strategy import URLStrategy
from bengal.utils.page_initializer import PageInitializer

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.page import Page
    from bengal.core.section import Section


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

