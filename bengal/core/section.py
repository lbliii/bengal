"""
Section Object - Represents a folder or logical grouping of pages.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from bengal.core.page import Page


@dataclass
class Section:
    """
    Represents a folder or logical grouping of pages.
    
    Attributes:
        name: Section name
        path: Path to the section directory
        pages: List of pages in this section
        subsections: Child sections
        metadata: Section-level metadata
        index_page: Optional index page for the section
        parent: Parent section (if nested)
    """
    
    name: str
    path: Path
    pages: List[Page] = field(default_factory=list)
    subsections: List['Section'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    index_page: Optional[Page] = None
    parent: Optional['Section'] = None
    
    # Reference to site (set during site building)
    _site: Optional[Any] = field(default=None, repr=False)
    
    @property
    def title(self) -> str:
        """Get section title from metadata or generate from name."""
        return self.metadata.get("title", self.name.replace("-", " ").title())
    
    @property
    def hierarchy(self) -> List[str]:
        """
        Get the full hierarchy path of this section.
        
        Returns:
            List of section names from root to this section
        """
        if self.parent:
            return self.parent.hierarchy + [self.name]
        return [self.name]
    
    @property
    def depth(self) -> int:
        """Get the depth of this section in the hierarchy."""
        return len(self.hierarchy)
    
    # Section navigation properties
    
    @property
    def regular_pages(self) -> List[Page]:
        """
        Get only regular pages (non-sections) in this section.
        
        Returns:
            List of regular Page objects (excludes subsections)
            
        Example:
            {% for page in section.regular_pages %}
              <article>{{ page.title }}</article>
            {% endfor %}
        """
        return [p for p in self.pages if not isinstance(p, Section)]
    
    @property
    def sections(self) -> List['Section']:
        """
        Get immediate child sections.
        
        Returns:
            List of child Section objects
            
        Example:
            {% for subsection in section.sections %}
              <h3>{{ subsection.title }}</h3>
            {% endfor %}
        """
        return self.subsections
    
    @property
    def regular_pages_recursive(self) -> List[Page]:
        """
        Get all regular pages recursively (including from subsections).
        
        Returns:
            List of all descendant regular pages
            
        Example:
            <p>Total pages: {{ section.regular_pages_recursive | length }}</p>
        """
        result = list(self.regular_pages)
        for subsection in self.subsections:
            result.extend(subsection.regular_pages_recursive)
        return result
    
    @property
    def url(self) -> str:
        """
        Get the URL for this section.
        
        Returns:
            URL path for the section
        """
        # If we have an index page with a proper output_path, use its URL
        if (self.index_page and 
            hasattr(self.index_page, 'output_path') and 
            self.index_page.output_path):
            return self.index_page.url
        
        # Otherwise, construct from section hierarchy
        # This handles the case before pages have output_paths set
        if self.parent:
            # Nested section - include parent URL
            return f"{self.parent.url}{self.name}/"
        else:
            # Top-level section (no parent)
            return f"/{self.name}/"
    
    def add_page(self, page: Page) -> None:
        """
        Add a page to this section.
        
        Args:
            page: Page to add
        """
        self.pages.append(page)
        
        # Set as index page if it's named index.md or _index.md
        if page.source_path.stem in ("index", "_index"):
            self.index_page = page
            
            # Extract cascade metadata from index page for inheritance
            if 'cascade' in page.metadata:
                self.metadata['cascade'] = page.metadata['cascade']
    
    def add_subsection(self, section: 'Section') -> None:
        """
        Add a subsection to this section.
        
        Args:
            section: Child section to add
        """
        section.parent = self
        self.subsections.append(section)
    
    def needs_auto_index(self) -> bool:
        """
        Check if this section needs an auto-generated index page.
        
        Returns:
            True if section needs auto-generated index (no explicit _index.md)
        """
        return self.name != 'root' and self.index_page is None
    
    def has_index(self) -> bool:
        """
        Check if section has a valid index page.
        
        Returns:
            True if section has an index page (explicit or auto-generated)
        """
        return self.index_page is not None
    
    def get_all_pages(self, recursive: bool = True) -> List[Page]:
        """
        Get all pages in this section.
        
        Args:
            recursive: If True, include pages from subsections
            
        Returns:
            List of all pages
        """
        all_pages = list(self.pages)
        
        if recursive:
            for subsection in self.subsections:
                all_pages.extend(subsection.get_all_pages(recursive=True))
        
        return all_pages
    
    def aggregate_content(self) -> Dict[str, Any]:
        """
        Aggregate content from all pages in this section.
        
        Returns:
            Dictionary with aggregated content information
        """
        pages = self.get_all_pages(recursive=False)
        
        # Collect all tags
        all_tags = set()
        for page in pages:
            all_tags.update(page.tags)
        
        return {
            "page_count": len(pages),
            "total_page_count": len(self.get_all_pages(recursive=True)),
            "subsection_count": len(self.subsections),
            "tags": sorted(all_tags),
            "title": self.title,
            "hierarchy": self.hierarchy,
        }
    
    def apply_section_template(self, template_engine: Any) -> str:
        """
        Apply a section template to generate a section index page.
        
        Args:
            template_engine: Template engine instance
            
        Returns:
            Rendered HTML for the section index
        """
        context = {
            "section": self,
            "pages": self.pages,
            "subsections": self.subsections,
            "metadata": self.metadata,
            "aggregated": self.aggregate_content(),
        }
        
        # Use the index page if available, otherwise generate a listing
        if self.index_page:
            return self.index_page.rendered_html
        
        # Template rendering will be handled by the template engine
        return ""
    
    def walk(self) -> List['Section']:
        """
        Iteratively walk through all sections in the hierarchy.
        
        Returns:
            List of all sections (self and descendants)
        """
        sections = [self]
        stack = list(self.subsections)
        
        while stack:
            section = stack.pop()
            sections.append(section)
            stack.extend(section.subsections)
        
        return sections
    
    def __repr__(self) -> str:
        return f"Section(name='{self.name}', pages={len(self.pages)}, subsections={len(self.subsections)})"

