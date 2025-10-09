"""
Section orchestration for Bengal SSG.

Handles section lifecycle: ensuring all sections have index pages,
validation, and structural integrity.
"""

from pathlib import Path
from typing import TYPE_CHECKING, List

from bengal.utils.url_strategy import URLStrategy
from bengal.utils.page_initializer import PageInitializer
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.section import Section
    from bengal.core.page import Page


class SectionOrchestrator:
    """
    Handles section structure and completeness.
    
    Responsibilities:
    - Ensure all sections have index pages (explicit or auto-generated)
    - Generate archive pages for sections without _index.md
    - Validate section structure
    - Maintain section hierarchy integrity
    
    This orchestrator implements the "structural" concerns of sections,
    separate from cross-cutting concerns like taxonomies (tags, categories).
    """
    
    def __init__(self, site: 'Site'):
        """
        Initialize section orchestrator.
        
        Args:
            site: Site instance to manage sections for
        """
        self.site = site
        self.url_strategy = URLStrategy()
        self.initializer = PageInitializer(site)
    
    def finalize_sections(self) -> None:
        """
        Finalize all sections by ensuring they have index pages.
        
        For each section:
        - If it has an explicit _index.md, leave it alone
        - If it doesn't have an index page, generate an archive page
        - Recursively process subsections
        
        This ensures all section URLs resolve to valid pages.
        """
        logger.info("section_finalization_start", section_count=len(self.site.sections))
        
        archive_count = 0
        for section in self.site.sections:
            archives_created = self._finalize_recursive(section)
            archive_count += archives_created
        
        logger.info("section_finalization_complete", archives_created=archive_count)
    
    def _finalize_recursive(self, section: 'Section') -> int:
        """
        Recursively finalize a section and its subsections.
        
        Args:
            section: Section to finalize
            
        Returns:
            Number of archive pages created
        """
        archive_count = 0
        
        # Skip root section (no index needed)
        if section.name == 'root':
            # Still process subsections
            for subsection in section.subsections:
                archive_count += self._finalize_recursive(subsection)
            return archive_count
        
        # Ensure this section has an index page
        if not section.index_page:
            # Generate archive index
            archive_page = self._create_archive_index(section)
            section.index_page = archive_page
            self.site.pages.append(archive_page)
            archive_count += 1
            
            logger.debug(
                "section_archive_created",
                section_name=section.name,
                section_path=str(section.path),
                page_count=len(section.pages)
            )
        
        # Recursively finalize subsections
        for subsection in section.subsections:
            archive_count += self._finalize_recursive(subsection)
        
        return archive_count
    
    def _detect_content_type(self, section: 'Section') -> str:
        """
        Detect what kind of content this section contains.
        
        Uses convention over configuration:
        1. Explicit metadata override (highest priority)
        2. Section name patterns (api, cli, etc.)
        3. Content analysis (check page metadata)
        4. Date-based heuristic (has dates = archive)
        5. Default to generic list (not archive)
        
        Args:
            section: Section to analyze
            
        Returns:
            Content type: 'api-reference', 'cli-reference', 'tutorial', 'archive', or 'list'
        """
        # 1. Explicit override (highest priority)
        if 'content_type' in section.metadata:
            return section.metadata['content_type']
        
        # 2. Convention: section name patterns
        name = section.name.lower()
        
        if name in ('api', 'reference', 'api-reference', 'api-docs'):
            return 'api-reference'
        
        if name in ('cli', 'commands', 'cli-reference', 'command-line'):
            return 'cli-reference'
        
        if name in ('tutorials', 'guides', 'how-to'):
            return 'tutorial'
        
        # Blog/news sections (chronological)
        if name in ('blog', 'posts', 'news', 'articles'):
            return 'archive'
        
        # 3. Content analysis: check page metadata
        if section.pages:
            # Sample first few pages to detect type
            pages_with_dates = 0
            
            for page in section.pages[:5]:
                page_type = page.metadata.get('type', '')
                
                if 'python-module' in page_type or 'api-reference' in page_type:
                    return 'api-reference'
                
                if 'cli-' in page_type or page_type == 'command':
                    return 'cli-reference'
                
                # Check if page has a date (blog/archive indicator)
                if page.metadata.get('date') or page.date:
                    pages_with_dates += 1
            
            # 4. If most pages have dates, treat as chronological archive
            if pages_with_dates >= len(section.pages[:5]) * 0.6:
                return 'archive'
        
        # 5. Default: generic list page (not chronological archive)
        return 'list'
    
    def _should_paginate(self, section: 'Section', content_type: str) -> bool:
        """
        Determine if section should have pagination.
        
        Reference documentation (API, CLI, tutorials) should NOT be paginated.
        Blog-style archives should be paginated if they have many items.
        
        Args:
            section: Section to check
            content_type: Detected content type
            
        Returns:
            True if section should have pagination
        """
        # Reference docs: NEVER paginate
        if content_type in ('api-reference', 'cli-reference', 'tutorial'):
            return False
        
        # Archives: paginate if many items
        if content_type == 'archive':
            page_count = len(section.pages)
            threshold = self.site.config.get('pagination', {}).get('threshold', 20)
            return page_count > threshold
        
        # Explicit pagination control
        return section.metadata.get('paginate', False)
    
    def _get_template_for_content_type(self, content_type: str) -> str:
        """
        Get the appropriate template for a content type.
        
        Template hierarchy:
        - archive.html: Chronological/blog content with dates and pagination
        - index.html: Generic section landing page (fallback)
        - {type}/list.html: Specialized reference docs (api, cli, tutorial)
        
        Args:
            content_type: Type of content
            
        Returns:
            Template name
        """
        template_map = {
            'api-reference': 'api-reference/list.html',
            'cli-reference': 'cli-reference/list.html',
            'tutorial': 'tutorial/list.html',
            'archive': 'archive.html',
            'list': 'index.html',  # Generic fallback for non-chronological sections
        }
        return template_map.get(content_type, 'index.html')
    
    def _create_archive_index(self, section: 'Section') -> 'Page':
        """
        Create an auto-generated index page for a section.
        
        Detects content type and uses appropriate template:
        - API reference docs: api-reference/list.html (no pagination)
        - CLI reference docs: cli-reference/list.html (no pagination)
        - Tutorial sections: tutorial/list.html (no pagination)
        - Blog/chronological: archive.html (with pagination)
        - Generic sections: index.html (fallback)
        
        Args:
            section: Section that needs an index page
            
        Returns:
            Page object representing the section index
        """
        from bengal.core.page import Page
        from bengal.utils.pagination import Paginator
        
        # Create virtual path for generated archive (delegate to utility)
        virtual_path = self.url_strategy.make_virtual_path(
            self.site, 'archives', section.name
        )
        
        # Detect content type
        content_type = self._detect_content_type(section)
        
        # Determine template
        template = self._get_template_for_content_type(content_type)
        
        # Base metadata
        metadata = {
            'title': section.title,
            'template': template,
            'type': content_type,
            '_generated': True,
            '_virtual': True,
            '_section': section,
            '_posts': section.pages,
            '_subsections': section.subsections,
            '_content_type': content_type,
        }
        
        # Add pagination only if appropriate
        if self._should_paginate(section, content_type):
            paginator = Paginator(
                items=section.pages,
                per_page=self.site.config.get('pagination', {}).get('per_page', 10)
            )
            metadata.update({
                '_paginator': paginator,
                '_page_num': 1,
            })
        
        # Create archive page
        archive_page = Page(
            source_path=virtual_path,
            content="",
            metadata=metadata
        )
        
        # Compute output path using centralized logic
        archive_page.output_path = self.url_strategy.compute_archive_output_path(
            section=section,
            page_num=1,
            site=self.site
        )
        
        # Ensure page is correctly initialized (sets _site, validates)
        self.initializer.ensure_initialized_for_section(archive_page, section)
        
        return archive_page
    
    def validate_sections(self) -> List[str]:
        """
        Validate that all sections have valid index pages.
        
        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []
        for section in self.site.sections:
            errors.extend(self._validate_recursive(section))
        return errors
    
    def _validate_recursive(self, section: 'Section') -> List[str]:
        """
        Recursively validate a section and its subsections.
        
        Args:
            section: Section to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Skip root section
        if section.name == 'root':
            # Still validate subsections
            for subsection in section.subsections:
                errors.extend(self._validate_recursive(subsection))
            return errors
        
        # Check if section has index page
        if not section.index_page:
            errors.append(
                f"Section '{section.name}' at {section.path} has no index page. "
                "This should not happen after finalization."
            )
        
        # Note: We don't validate output paths here because they're set later
        # in the render phase. This validation runs in Phase 2 (finalization),
        # while output paths are set in Phase 6 (rendering).
        
        # Recursively validate subsections
        for subsection in section.subsections:
            errors.extend(self._validate_recursive(subsection))
        
        return errors

