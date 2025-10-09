"""
Page Object - Represents a single content page.

This module provides the main Page class, which combines multiple mixins
to provide a complete page interface while maintaining separation of concerns.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .metadata import PageMetadataMixin
from .navigation import PageNavigationMixin
from .computed import PageComputedMixin
from .relationships import PageRelationshipsMixin
from .operations import PageOperationsMixin


@dataclass
class Page(
    PageMetadataMixin,
    PageNavigationMixin,
    PageComputedMixin,
    PageRelationshipsMixin,
    PageOperationsMixin
):
    """
    Represents a single content page.
    
    BUILD LIFECYCLE:
    ================
    Pages progress through distinct build phases. Properties have different
    availability depending on the current phase:
    
    1. Discovery (content_discovery.py)
       ✅ Available: source_path, content, metadata, title, slug, date
       ❌ Not available: toc, parsed_ast, toc_items, rendered_html
    
    2. Parsing (pipeline.py)
       ✅ Available: All Stage 1 + toc, parsed_ast
       ✅ toc_items can be accessed (will extract from toc)
    
    3. Rendering (pipeline.py)
       ✅ Available: All previous + rendered_html, output_path
       ✅ All properties fully populated
    
    Note: Some properties like toc_items can be accessed early (returning [])
    but won't cache empty results, allowing proper extraction after parsing.
    
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
        related_posts: Related pages (pre-computed during build based on tag overlap)
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
    related_posts: List['Page'] = field(default_factory=list)  # Pre-computed during build
    
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
    
    def __repr__(self) -> str:
        return f"Page(title='{self.title}', source='{self.source_path}')"


__all__ = ['Page']

