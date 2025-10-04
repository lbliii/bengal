"""
Section orchestration for Bengal SSG.

Handles section lifecycle: ensuring all sections have index pages,
validation, and structural integrity.
"""

from pathlib import Path
from typing import TYPE_CHECKING, List

from bengal.utils.url_strategy import URLStrategy
from bengal.utils.page_initializer import PageInitializer

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
        for section in self.site.sections:
            self._finalize_recursive(section)
    
    def _finalize_recursive(self, section: 'Section') -> None:
        """
        Recursively finalize a section and its subsections.
        
        Args:
            section: Section to finalize
        """
        # Skip root section (no index needed)
        if section.name == 'root':
            # Still process subsections
            for subsection in section.subsections:
                self._finalize_recursive(subsection)
            return
        
        # Ensure this section has an index page
        if not section.index_page:
            # Generate archive index
            archive_page = self._create_archive_index(section)
            section.index_page = archive_page
            self.site.pages.append(archive_page)
        
        # Recursively finalize subsections
        for subsection in section.subsections:
            self._finalize_recursive(subsection)
    
    def _create_archive_index(self, section: 'Section') -> 'Page':
        """
        Create an auto-generated archive index page for a section.
        
        Args:
            section: Section that needs an archive index
            
        Returns:
            Page object representing the archive index
        """
        from bengal.core.page import Page
        from bengal.utils.pagination import Paginator
        
        # Create virtual path for generated archive (delegate to utility)
        virtual_path = self.url_strategy.make_virtual_path(
            self.site, 'archives', section.name
        )
        
        # Create paginator for the section's pages
        paginator = Paginator(
            items=section.pages,
            per_page=self.site.config.get('pagination', {}).get('per_page', 10)
        )
        
        # Create archive page with metadata
        archive_page = Page(
            source_path=virtual_path,
            content="",
            metadata={
                'title': section.title,
                'template': 'archive.html',
                'type': 'archive',
                '_generated': True,
                '_virtual': True,
                '_section': section,
                '_posts': section.pages,
                '_subsections': section.subsections,
                '_paginator': paginator,
                '_page_num': 1,
            }
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

