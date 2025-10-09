"""
Page Metadata Mixin - Basic properties and type checking.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import re

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class PageMetadataMixin:
    """
    Mixin providing metadata properties and type checking for pages.
    
    This mixin handles:
    - Basic properties: title, date, slug, url
    - Type checking: is_home, is_section, is_page, kind
    - Simple metadata: description, draft, keywords
    - TOC access: toc_items (lazy evaluation)
    """
    
    @property
    def title(self) -> str:
        """Get page title from metadata or generate from filename."""
        return self.metadata.get("title", self.source_path.stem.replace("-", " ").title())
    
    @property
    def date(self) -> Optional[datetime]:
        """Get page date from metadata."""
        from datetime import date as date_type
        
        date_value = self.metadata.get("date")
        if isinstance(date_value, datetime):
            return date_value
        elif isinstance(date_value, date_type):
            # Convert date to datetime
            return datetime.combine(date_value, datetime.min.time())
        elif isinstance(date_value, str):
            # Try parsing string dates
            try:
                return datetime.fromisoformat(date_value)
            except (ValueError, AttributeError):
                pass
        return None
    
    @property
    def slug(self) -> str:
        """Get URL slug for the page."""
        # Check metadata first
        if "slug" in self.metadata:
            return self.metadata["slug"]
        
        # Special handling for _index.md files
        if self.source_path.stem == "_index":
            # Use the parent directory name as the slug
            return self.source_path.parent.name
        
        return self.source_path.stem
    
    @property
    def url(self) -> str:
        """
        Get the URL path for the page.
        
        Generates clean URLs from output paths, handling:
        - Pretty URLs (about/index.html -> /about/)
        - Index pages (docs/index.html -> /docs/)
        - Root index (index.html -> /)
        - Edge cases (missing site reference, invalid paths)
        
        Returns:
            URL path with leading and trailing slashes
        """
        # Fallback if no output path set
        if not self.output_path:
            return self._fallback_url()
        
        # Need site reference to compute relative path
        if not self._site:
            return self._fallback_url()
        
        try:
            # Compute relative path from actual output directory
            rel_path = self.output_path.relative_to(self._site.output_dir)
        except ValueError:
            # output_path not under output_dir - should never happen
            # but handle gracefully with warning
            logger.warning("page_output_path_mismatch",
                          output_path=str(self.output_path),
                          output_dir=str(self._site.output_dir),
                          page_source=str(getattr(self, 'source_path', 'unknown')))
            return self._fallback_url()
        
        # Convert Path to URL components
        url_parts = list(rel_path.parts)
        
        # Remove 'index.html' from end (it's implicit in URLs)
        if url_parts and url_parts[-1] == 'index.html':
            url_parts = url_parts[:-1]
        elif url_parts and url_parts[-1].endswith('.html'):
            # For non-index pages, remove .html extension
            # e.g., about.html -> about
            url_parts[-1] = url_parts[-1][:-5]
        
        # Construct URL with leading and trailing slashes
        if not url_parts:
            # Root index page
            return '/'
        
        url = '/' + '/'.join(url_parts)
        
        # Ensure trailing slash for directory-like URLs
        if not url.endswith('/'):
            url += '/'
        
        return url
    
    def _fallback_url(self) -> str:
        """
        Generate fallback URL when output_path or site not available.
        
        Used during page construction before output_path is determined.
        
        Returns:
            URL based on slug
        """
        return f"/{self.slug}/"
    
    @property
    def toc_items(self) -> List[Dict[str, Any]]:
        """
        Get structured TOC data (lazy evaluation).
        
        Only extracts TOC structure when accessed by templates, saving
        HTMLParser overhead for pages that don't use toc_items.
        
        Important: This property does NOT cache empty results. This allows
        toc_items to be accessed before parsing (during xref indexing) without
        preventing extraction after parsing when page.toc is actually set.
        
        Returns:
            List of TOC items with id, title, and level
        """
        # Only extract and cache if we haven't extracted yet AND toc exists
        # Don't cache empty results - toc might be set later during parsing
        if self._toc_items_cache is None and self.toc:
            # Import here to avoid circular dependency
            from bengal.rendering.pipeline import extract_toc_structure
            self._toc_items_cache = extract_toc_structure(self.toc)
        
        # Return cached value if we have it, otherwise empty list
        # (but don't cache the empty list - allow re-evaluation when toc is set)
        return self._toc_items_cache if self._toc_items_cache is not None else []
    
    @property
    def is_home(self) -> bool:
        """
        Check if this page is the home page.
        
        Returns:
            True if this is the home page
            
        Example:
            {% if page.is_home %}
              <h1>Welcome to the home page!</h1>
            {% endif %}
        """
        return self.url == '/' or self.slug in ('index', '_index', 'home')
    
    @property
    def is_section(self) -> bool:
        """
        Check if this page is a section page.
        
        Returns:
            True if this is a section (always False for Page, True for Section)
            
        Example:
            {% if page.is_section %}
              <h2>Section: {{ page.title }}</h2>
            {% endif %}
        """
        # Import here to avoid circular import
        from bengal.core.section import Section
        return isinstance(self, Section)
    
    @property
    def is_page(self) -> bool:
        """
        Check if this is a regular page (not a section).
        
        Returns:
            True if this is a regular page
            
        Example:
            {% if page.is_page %}
              <article>{{ page.content }}</article>
            {% endif %}
        """
        return not self.is_section
    
    @property
    def kind(self) -> str:
        """
        Get the kind of page: 'home', 'section', or 'page'.
        
        Returns:
            String indicating page kind
            
        Example:
            {% if page.kind == 'section' %}
              {# Render section template #}
            {% endif %}
        """
        if self.is_home:
            return 'home'
        elif self.is_section:
            return 'section'
        return 'page'
    
    @property
    def description(self) -> str:
        """
        Get page description from metadata.
        
        Returns:
            Page description or empty string
        """
        return self.metadata.get('description', '')
    
    @property
    def draft(self) -> bool:
        """
        Check if page is marked as draft.
        
        Returns:
            True if page is a draft
        """
        return self.metadata.get('draft', False)
    
    @property
    def keywords(self) -> List[str]:
        """
        Get page keywords from metadata.
        
        Returns:
            List of keywords
        """
        keywords = self.metadata.get('keywords', [])
        if isinstance(keywords, str):
            # Split comma-separated keywords
            return [k.strip() for k in keywords.split(',')]
        return keywords if isinstance(keywords, list) else []

