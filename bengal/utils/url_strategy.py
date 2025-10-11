"""
URL Strategy - Centralized URL and path computation.

Provides pure utility functions for computing output paths and URLs.
Used by orchestrators to ensure consistent path generation across the system.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site


class URLStrategy:
    """
    Pure utility for URL and output path computation.
    
    Centralizes all path/URL logic to ensure consistency and prevent bugs.
    All methods are static - no state, pure logic.
    
    Design principles:
    - Pure functions (no side effects)
    - No dependencies on global state
    - Easy to test in isolation
    - Reusable across orchestrators
    """
    
    @staticmethod
    def compute_regular_page_output_path(page: 'Page', site: 'Site') -> Path:
        """
        Compute output path for a regular content page.
        
        Args:
            page: Page object (must have source_path set)
            site: Site object (for output_dir and config)
            
        Returns:
            Absolute path where the page HTML should be written
            
        Examples:
            content/about.md → public/about/index.html (pretty URLs)
            content/blog/post.md → public/blog/post/index.html
            content/docs/_index.md → public/docs/index.html
        """
        content_dir = site.root_path / "content"
        pretty_urls = site.config.get('pretty_urls', True)
        # i18n configuration (optional)
        i18n = site.config.get('i18n', {}) or {}
        strategy = i18n.get('strategy', 'none')
        default_lang = i18n.get('default_language', 'en')
        default_in_subdir = bool(i18n.get('default_in_subdir', False))
        
        # Get relative path from content directory
        try:
            rel_path = page.source_path.relative_to(content_dir)
        except ValueError:
            # Not under content_dir (shouldn't happen for regular pages)
            rel_path = Path(page.source_path.name)
        
        # Change extension to .html
        output_rel_path = rel_path.with_suffix('.html')
        
        # Apply URL rules
        if pretty_urls:
            if output_rel_path.stem in ("index", "_index"):
                # _index.md → index.html (keep in same directory)
                output_rel_path = output_rel_path.parent / "index.html"
            else:
                # about.md → about/index.html (directory structure)
                output_rel_path = output_rel_path.parent / output_rel_path.stem / "index.html"
        # Flat URLs: about.md → about.html
        elif output_rel_path.stem == "_index":
            output_rel_path = output_rel_path.parent / "index.html"
        
        # Apply i18n URL strategy (prefix)
        if strategy == 'prefix':
            lang: str | None = getattr(page, 'lang', None)
            if lang:
                # If default language should be under subdir or non-default language: prefix
                if default_in_subdir or lang != default_lang:
                    output_rel_path = Path(lang) / output_rel_path
        # strategy 'domain' or 'none' → no path prefixing here
        return site.output_dir / output_rel_path
    
    @staticmethod
    def compute_archive_output_path(
        section: 'Section',
        page_num: int,
        site: 'Site'
    ) -> Path:
        """
        Compute output path for a section archive page.
        
        Args:
            section: Section to create archive for
            page_num: Page number (1 for first page, 2+ for pagination)
            site: Site object (for output_dir)
            
        Returns:
            Absolute path where the archive HTML should be written
            
        Examples:
            section='docs', page=1 → public/docs/index.html
            section='docs', page=2 → public/docs/page/2/index.html
            section='docs/markdown', page=1 → public/docs/markdown/index.html
        """
        # Get full hierarchy (excluding 'root')
        hierarchy = [h for h in section.hierarchy if h != 'root']
        
        # Build base path
        path = site.output_dir
        for segment in hierarchy:
            path = path / segment
        
        # Add pagination if needed
        if page_num > 1:
            path = path / "page" / str(page_num)
        
        return path / "index.html"
    
    @staticmethod
    def compute_tag_output_path(
        tag_slug: str,
        page_num: int,
        site: 'Site'
    ) -> Path:
        """
        Compute output path for a tag listing page.
        
        Args:
            tag_slug: URL-safe tag identifier
            page_num: Page number (1 for first page, 2+ for pagination)
            site: Site object (for output_dir)
            
        Returns:
            Absolute path where the tag page HTML should be written
            
        Examples:
            tag='python', page=1 → public/tags/python/index.html
            tag='python', page=2 → public/tags/python/page/2/index.html
        """
        # i18n prefix support using site's current language context
        i18n = site.config.get('i18n', {}) or {}
        strategy = i18n.get('strategy', 'none')
        default_lang = i18n.get('default_language', 'en')
        default_in_subdir = bool(i18n.get('default_in_subdir', False))
        lang = getattr(site, 'current_language', None)

        base_path = site.output_dir
        if strategy == 'prefix' and lang:
            if default_in_subdir or lang != default_lang:
                base_path = base_path / lang

        path = base_path / "tags" / tag_slug
        
        # Add pagination if needed
        if page_num > 1:
            path = path / "page" / str(page_num)
        
        return path / "index.html"
    
    @staticmethod
    def compute_tag_index_output_path(site: 'Site') -> Path:
        """
        Compute output path for the main tags index page.
        
        Args:
            site: Site object (for output_dir)
            
        Returns:
            Absolute path where the tags index HTML should be written
            
        Example:
            public/tags/index.html
        """
        # i18n prefix support using site's current language context
        i18n = site.config.get('i18n', {}) or {}
        strategy = i18n.get('strategy', 'none')
        default_lang = i18n.get('default_language', 'en')
        default_in_subdir = bool(i18n.get('default_in_subdir', False))
        lang = getattr(site, 'current_language', None)

        base_path = site.output_dir
        if strategy == 'prefix' and lang:
            if default_in_subdir or lang != default_lang:
                base_path = base_path / lang

        return base_path / "tags" / "index.html"
    
    @staticmethod
    def url_from_output_path(output_path: Path, site: 'Site') -> str:
        """
        Generate clean URL from output path.
        
        Args:
            output_path: Absolute path to output file
            site: Site object (for output_dir)
            
        Returns:
            Clean URL with leading/trailing slashes
            
        Examples:
            public/about/index.html → /about/
            public/docs/guide.html → /docs/guide/
            public/index.html → /
            
        Raises:
            ValueError: If output_path is not under site.output_dir
        """
        try:
            rel_path = output_path.relative_to(site.output_dir)
        except ValueError:
            raise ValueError(
                f"Output path {output_path} is not under output directory {site.output_dir}"
            )
        
        # Convert to URL parts
        url_parts = list(rel_path.parts)
        
        # Remove index.html (implicit in URLs)
        if url_parts and url_parts[-1] == 'index.html':
            url_parts = url_parts[:-1]
        elif url_parts and url_parts[-1].endswith('.html'):
            # Non-index: remove .html extension
            url_parts[-1] = url_parts[-1][:-5]
        
        # Build URL
        if not url_parts:
            return '/'
        
        url = '/' + '/'.join(url_parts)
        
        # Ensure trailing slash
        if not url.endswith('/'):
            url += '/'
        
        return url
    
    @staticmethod
    def make_virtual_path(site: 'Site', *parts: str) -> Path:
        """
        Create virtual source path for generated pages.
        
        Generated pages (archives, tags, etc.) don't have real source files.
        This creates a virtual path under .bengal/generated/ for tracking.
        
        Args:
            site: Site object (for root_path)
            *parts: Path components
            
        Returns:
            Virtual path under .bengal/generated/
            
        Examples:
            make_virtual_path(site, 'archives', 'docs')
            → /path/to/site/.bengal/generated/archives/docs/index.md
            
            make_virtual_path(site, 'tags', 'python')
            → /path/to/site/.bengal/generated/tags/python/index.md
        """
        return (
            site.root_path /
            ".bengal" /
            "generated" /
            Path(*parts) /
            "index.md"
        )

