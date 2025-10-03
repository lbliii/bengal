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
    toc_items: List[Dict[str, Any]] = field(default_factory=list)
    
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
        date_value = self.metadata.get("date")
        if isinstance(date_value, datetime):
            return date_value
        return None
    
    @property
    def slug(self) -> str:
        """Get URL slug for the page."""
        return self.metadata.get("slug", self.source_path.stem)
    
    @property
    def url(self) -> str:
        """Get the URL path for the page."""
        if self.output_path:
            # Convert output path to URL path
            # e.g., public/posts/my-post/index.html -> /posts/my-post/
            parts = self.output_path.parts
            
            # Find where the path starts (after 'public' or similar output dir)
            try:
                # Common output directories
                for output_dir in ['public', 'dist', 'build', '_site']:
                    if output_dir in parts:
                        start_idx = parts.index(output_dir) + 1
                        url_parts = parts[start_idx:]
                        break
                else:
                    # If no standard output dir found, use all parts
                    url_parts = parts
                
                # Remove 'index.html' from the end
                if url_parts and url_parts[-1] == 'index.html':
                    url_parts = url_parts[:-1]
                
                # Construct URL
                url = '/' + '/'.join(url_parts)
                if url != '/' and not url.endswith('/'):
                    url += '/'
                
                return url
            except (ValueError, IndexError):
                pass
        
        # Fallback: construct from slug
        return f'/{self.slug}/'
    
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

