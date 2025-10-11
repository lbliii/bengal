"""
Page Initializer - Ensures pages are correctly initialized.

Validates that pages have all required references set before use.
Helps prevent bugs like missing _site references or output_paths.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


class PageInitializer:
    """
    Ensures pages are correctly initialized with all required references.
    
    Used by orchestrators after creating pages to validate they're ready for use.
    
    Design principles:
    - Fail fast (errors at initialization, not at URL generation)
    - Clear error messages (tell developer exactly what's wrong)
    - Single responsibility (just validation, not creation)
    - Lightweight (minimal logic, mostly checks)
    
    Usage:
        # In an orchestrator
        def __init__(self, site):
            self.initializer = PageInitializer(site)
        
        def create_my_page(self):
            page = Page(...)
            page.output_path = compute_path(...)
            self.initializer.ensure_initialized(page)  # Validate!
            return page
    """
    
    def __init__(self, site: 'Site'):
        """
        Initialize the page initializer.
        
        Args:
            site: Site object to associate with pages
        """
        self.site = site
    
    def ensure_initialized(self, page: 'Page') -> None:
        """
        Ensure a page is correctly initialized.
        
        Checks:
        1. Page has _site reference (or sets it)
        2. Page has output_path set
        3. Page URL generation works
        
        Args:
            page: Page to validate and initialize
            
        Raises:
            ValueError: If page is missing required attributes or URL generation fails
        """
        # Set site reference if missing
        if not page._site:
            page._site = self.site
        
        # Validate output_path is set
        if not page.output_path:
            raise ValueError(
                f"Page '{page.title}' has no output_path set. "
                f"Orchestrator must compute and set output_path before calling ensure_initialized().\n"
                f"Source: {page.source_path}"
            )
        
        # Validate output_path is absolute
        if not page.output_path.is_absolute():
            raise ValueError(
                f"Page '{page.title}' has relative output_path: {page.output_path}\n"
                f"Output paths must be absolute. "
                f"Use site.output_dir as base."
            )
        
        # Verify URL generation works
        try:
            url = page.url
            if not url.startswith('/'):
                raise ValueError(f"Generated URL doesn't start with '/': {url}")
        except Exception as e:
            raise ValueError(
                f"Page '{page.title}' URL generation failed: {e}\n"
                f"Output path: {page.output_path}\n"
                f"Site output_dir: {self.site.output_dir}"
            ) from e
    
    def ensure_initialized_for_section(self, page: 'Page', section: 'Section') -> None:
        """
        Ensure a page is initialized with section reference.
        
        Like ensure_initialized() but also sets and validates the section reference.
        Used for archive pages and section index pages.
        
        Args:
            page: Page to validate and initialize
            section: Section this page belongs to
            
        Raises:
            ValueError: If page is missing required attributes or validation fails
        """
        # First do standard initialization
        self.ensure_initialized(page)
        
        # Set section reference
        if not page._section:
            page._section = section

