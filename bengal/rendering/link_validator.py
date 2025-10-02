"""
Link validation for catching broken links.
"""

from typing import Any, List
from pathlib import Path
import re

from bengal.core.page import Page


class LinkValidator:
    """
    Validates links in pages to catch broken links.
    """
    
    def __init__(self) -> None:
        """Initialize the link validator."""
        self.validated_urls: set = set()
        self.broken_links: List[tuple] = []
    
    def validate_page_links(self, page: Page) -> List[str]:
        """
        Validate all links in a page.
        
        Args:
            page: Page to validate
            
        Returns:
            List of broken link URLs
        """
        broken = []
        
        for link in page.links:
            if not self._is_valid_link(link, page):
                broken.append(link)
                self.broken_links.append((page.source_path, link))
        
        return broken
    
    def validate_site(self, site: Any) -> List[tuple]:
        """
        Validate all links in the entire site.
        
        Args:
            site: Site instance
            
        Returns:
            List of (page_path, broken_link) tuples
        """
        self.broken_links = []
        
        for page in site.pages:
            self.validate_page_links(page)
        
        if self.broken_links:
            print(f"\nWarning: Found {len(self.broken_links)} broken links:")
            for page_path, link in self.broken_links[:10]:  # Show first 10
                print(f"  - {page_path}: {link}")
            
            if len(self.broken_links) > 10:
                print(f"  ... and {len(self.broken_links) - 10} more")
        
        return self.broken_links
    
    def _is_valid_link(self, link: str, page: Page) -> bool:
        """
        Check if a link is valid.
        
        Args:
            link: Link URL to check
            page: Page containing the link
            
        Returns:
            True if link is valid, False otherwise
        """
        # Skip external links (http/https)
        if link.startswith(('http://', 'https://', 'mailto:', 'tel:', '#')):
            return True
        
        # Skip data URLs
        if link.startswith('data:'):
            return True
        
        # Check if it's a relative link to another page
        # This is a simplified check - a full implementation would
        # resolve the link and check if the target exists
        
        # For now, assume internal links are valid
        # A full implementation would need to:
        # 1. Resolve the link relative to the page
        # 2. Check if the target file exists in the output
        # 3. Handle anchors (#sections)
        
        return True

