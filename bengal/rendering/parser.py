"""
Content parser for Markdown and other formats.
"""

from typing import Any, Dict
import markdown
from markdown.extensions import Extension
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension


class MarkdownParser:
    """
    Parser for Markdown content with support for extensions.
    """
    
    def __init__(self) -> None:
        """Initialize the Markdown parser with extensions."""
        self.md = markdown.Markdown(
            extensions=[
                'extra',
                'codehilite',
                'fenced_code',
                'tables',
                'toc',
                'meta',
                'attr_list',
                'def_list',
                'footnotes',
                'admonition',
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'linenums': False,
                },
                'toc': {
                    'permalink': True,
                    'toc_depth': '2-4',
                }
            }
        )
    
    def parse(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Parse Markdown content into HTML.
        
        Args:
            content: Raw Markdown content
            metadata: Page metadata
            
        Returns:
            Parsed HTML content
        """
        # Reset the parser for fresh parse
        self.md.reset()
        
        # Parse the content
        html = self.md.convert(content)
        
        return html
    
    def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]:
        """
        Parse Markdown content and extract table of contents.
        
        Args:
            content: Raw Markdown content
            metadata: Page metadata
            
        Returns:
            Tuple of (parsed HTML, table of contents HTML)
        """
        self.md.reset()
        html = self.md.convert(content)
        
        # Extract TOC if available
        toc = getattr(self.md, 'toc', '')
        
        return html, toc

