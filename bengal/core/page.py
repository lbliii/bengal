"""
Page Object - Represents a single content page.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class Page:
    """
    Represents a single content page.
    
    Attributes:
        source_path: Path to the source content file
        content: Raw content (Markdown, etc.)
        metadata: Frontmatter metadata (title, date, tags, etc.)
        parsed_ast: Abstract Syntax Tree from parsed content
        rendered_html: Rendered HTML output
        output_path: Path where the rendered page will be written
        links: List of links found in the page
        tags: Tags associated with the page
        version: Version information for versioned content
        toc: Table of contents HTML (auto-generated from headings)
        toc_items: Structured TOC data for custom rendering
    """
    
    source_path: Path
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    parsed_ast: Optional[Any] = None
    rendered_html: str = ""
    output_path: Optional[Path] = None
    links: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: Optional[str] = None
    toc: Optional[str] = None
    
    # References for navigation (set during site building)
    _site: Optional[Any] = field(default=None, repr=False)
    _section: Optional[Any] = field(default=None, repr=False)
    
    # Private cache for lazy toc_items property
    _toc_items_cache: Optional[List[Dict[str, Any]]] = field(default=None, repr=False, init=False)
    
    def __post_init__(self) -> None:
        """Initialize computed fields."""
        if self.metadata:
            self.tags = self.metadata.get("tags", [])
            self.version = self.metadata.get("version")
    
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
            print(f"⚠️  Warning: Page output path {self.output_path} "
                  f"is not under output directory {self._site.output_dir}")
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
        
        Returns:
            List of TOC items with id, title, and level
        """
        if self._toc_items_cache is None:
            if self.toc:
                # Import here to avoid circular dependency
                from bengal.rendering.pipeline import extract_toc_structure
                self._toc_items_cache = extract_toc_structure(self.toc)
            else:
                self._toc_items_cache = []
        
        return self._toc_items_cache
    
    # Navigation properties
    
    @property
    def next(self) -> Optional['Page']:
        """
        Get the next page in the site's collection of pages.
        
        Returns:
            Next page or None if this is the last page
            
        Example:
            {% if page.next %}
              <a href="{{ url_for(page.next) }}">{{ page.next.title }} →</a>
            {% endif %}
        """
        if not self._site or not hasattr(self._site, 'pages'):
            return None
        
        try:
            pages = self._site.pages
            idx = pages.index(self)
            if idx < len(pages) - 1:
                return pages[idx + 1]
        except (ValueError, IndexError):
            pass
        
        return None
    
    @property
    def prev(self) -> Optional['Page']:
        """
        Get the previous page in the site's collection of pages.
        
        Returns:
            Previous page or None if this is the first page
            
        Example:
            {% if page.prev %}
              <a href="{{ url_for(page.prev) }}">← {{ page.prev.title }}</a>
            {% endif %}
        """
        if not self._site or not hasattr(self._site, 'pages'):
            return None
        
        try:
            pages = self._site.pages
            idx = pages.index(self)
            if idx > 0:
                return pages[idx - 1]
        except (ValueError, IndexError):
            pass
        
        return None
    
    @property
    def next_in_section(self) -> Optional['Page']:
        """
        Get the next page within the same section.
        
        Returns:
            Next page in section or None
            
        Example:
            {% if page.next_in_section %}
              <a href="{{ url_for(page.next_in_section) }}">Next in section →</a>
            {% endif %}
        """
        if not self._section or not hasattr(self._section, 'pages'):
            return None
        
        try:
            section_pages = self._section.pages
            idx = section_pages.index(self)
            if idx < len(section_pages) - 1:
                return section_pages[idx + 1]
        except (ValueError, IndexError):
            pass
        
        return None
    
    @property
    def prev_in_section(self) -> Optional['Page']:
        """
        Get the previous page within the same section.
        
        Returns:
            Previous page in section or None
            
        Example:
            {% if page.prev_in_section %}
              <a href="{{ url_for(page.prev_in_section) }}">← Prev in section</a>
            {% endif %}
        """
        if not self._section or not hasattr(self._section, 'pages'):
            return None
        
        try:
            section_pages = self._section.pages
            idx = section_pages.index(self)
            if idx > 0:
                return section_pages[idx - 1]
        except (ValueError, IndexError):
            pass
        
        return None
    
    @property
    def parent(self) -> Optional[Any]:
        """
        Get the parent section of this page.
        
        Returns:
            Parent section or None
            
        Example:
            {% if page.parent %}
              <a href="{{ url_for(page.parent) }}">{{ page.parent.title }}</a>
            {% endif %}
        """
        return self._section
    
    @property
    def ancestors(self) -> List[Any]:
        """
        Get all ancestor sections of this page.
        
        Returns:
            List of ancestor sections from immediate parent to root
            
        Example:
            {% for ancestor in page.ancestors | reverse %}
              <a href="{{ url_for(ancestor) }}">{{ ancestor.title }}</a> /
            {% endfor %}
        """
        result = []
        current = self._section
        
        while current:
            result.append(current)
            current = getattr(current, 'parent', None)
        
        return result
    
    # Page type checking properties
    
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
    
    # Page comparison methods
    
    def eq(self, other: 'Page') -> bool:
        """
        Check if two pages are equal.
        
        Args:
            other: Page to compare with
            
        Returns:
            True if pages are the same
            
        Example:
            {% if page.eq(other_page) %}
              <p>Same page!</p>
            {% endif %}
        """
        if not isinstance(other, Page):
            return False
        return self.source_path == other.source_path
    
    def in_section(self, section: Any) -> bool:
        """
        Check if this page is in the given section.
        
        Args:
            section: Section to check
            
        Returns:
            True if page is in the section
            
        Example:
            {% if page.in_section(blog_section) %}
              <span class="badge">Blog Post</span>
            {% endif %}
        """
        return self._section == section
    
    def is_ancestor(self, other: 'Page') -> bool:
        """
        Check if this page is an ancestor of another page.
        
        Args:
            other: Page to check
            
        Returns:
            True if this page is an ancestor
            
        Example:
            {% if section.is_ancestor(page) %}
              <p>{{ page.title }} is a descendant</p>
            {% endif %}
        """
        if not self.is_section:
            return False
        
        # Check if other page is in this section or subsections
        return other._section in self.walk() if hasattr(self, 'walk') else False
    
    def is_descendant(self, other: 'Page') -> bool:
        """
        Check if this page is a descendant of another page.
        
        Args:
            other: Page to check
            
        Returns:
            True if this page is a descendant
            
        Example:
            {% if page.is_descendant(section) %}
              <p>Part of {{ section.title }}</p>
            {% endif %}
        """
        return other.is_ancestor(self) if hasattr(other, 'is_ancestor') else False
    
    def render(self, template_engine: Any) -> str:
        """
        Render the page using the provided template engine.
        
        Args:
            template_engine: Template engine instance
            
        Returns:
            Rendered HTML content
        """
        from bengal.rendering.renderer import Renderer
        
        renderer = Renderer(template_engine)
        self.rendered_html = renderer.render_page(self)
        return self.rendered_html
    
    def validate_links(self) -> List[str]:
        """
        Validate all links in the page.
        
        Returns:
            List of broken link URLs
        """
        from bengal.rendering.link_validator import LinkValidator
        
        validator = LinkValidator()
        broken_links = validator.validate_page_links(self)
        return broken_links
    
    def apply_template(self, template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Apply a specific template to this page.
        
        Args:
            template_name: Name of the template to apply
            context: Additional context variables
            
        Returns:
            Rendered content with template applied
        """
        full_context = {
            "page": self,
            "content": self.rendered_html or self.content,
            "title": self.title,
            "metadata": self.metadata,
            **(context or {})
        }
        
        # Template application will be handled by the template engine
        return self.rendered_html
    
    def extract_links(self) -> List[str]:
        """
        Extract all links from the page content.
        
        Returns:
            List of link URLs found in the page
        """
        import re
        
        # Extract Markdown links [text](url)
        markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', self.content)
        
        # Extract HTML links <a href="url">
        html_links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\']', self.content)
        
        self.links = [url for _, url in markdown_links] + html_links
        return self.links
    
    def __repr__(self) -> str:
        return f"Page(title='{self.title}', source='{self.source_path}')"

