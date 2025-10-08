"""
RSS feed generation.
"""

from pathlib import Path
from typing import Any
from datetime import datetime
import xml.etree.ElementTree as ET

from bengal.utils.logger import get_logger


class RSSGenerator:
    """
    Generates RSS feed for the site.
    """
    
    def __init__(self, site: Any) -> None:
        """
        Initialize RSS generator.
        
        Args:
            site: Site instance
        """
        self.site = site
        self.logger = get_logger(__name__)
    
    def generate(self) -> None:
        """Generate and write rss.xml."""
        # Add items (pages sorted by date)
        pages_with_dates = [p for p in self.site.pages if p.date]
        sorted_pages = sorted(pages_with_dates, key=lambda p: p.date, reverse=True)
        
        self.logger.info("rss_generation_start",
                        total_pages=len(self.site.pages),
                        pages_with_dates=len(pages_with_dates),
                        rss_limit=min(20, len(sorted_pages)))
        
        # Create root element
        rss = ET.Element('rss')
        rss.set('version', '2.0')
        
        channel = ET.SubElement(rss, 'channel')
        
        # Add channel metadata
        title = self.site.config.get('title', 'Bengal Site')
        baseurl = self.site.config.get('baseurl', '')
        description = self.site.config.get('description', f'{title} RSS Feed')
        
        ET.SubElement(channel, 'title').text = title
        ET.SubElement(channel, 'link').text = baseurl
        ET.SubElement(channel, 'description').text = description
        
        # Limit to most recent 20 items
        for page in sorted_pages[:20]:
            item = ET.SubElement(channel, 'item')
            
            ET.SubElement(item, 'title').text = page.title
            
            # Get page URL
            if page.output_path:
                try:
                    rel_path = page.output_path.relative_to(self.site.output_dir)
                    link = f"{baseurl}/{rel_path}".replace('\\', '/')
                    link = link.replace('/index.html', '/')
                except ValueError:
                    link = f"{baseurl}/{page.slug}/"
            else:
                link = f"{baseurl}/{page.slug}/"
            
            ET.SubElement(item, 'link').text = link
            ET.SubElement(item, 'guid').text = link
            
            # Add description (excerpt or full content)
            if 'description' in page.metadata:
                description = page.metadata['description']
            else:
                # Use first 200 characters of content as description
                content = page.content[:200] + '...' if len(page.content) > 200 else page.content
                description = content
            
            ET.SubElement(item, 'description').text = description
            
            # Add pubDate
            if page.date:
                # Format as RFC 822
                pubdate = page.date.strftime('%a, %d %b %Y %H:%M:%S +0000')
                ET.SubElement(item, 'pubDate').text = pubdate
        
        # Write RSS to file atomically (crash-safe)
        from bengal.utils.atomic_write import AtomicFile
        
        tree = ET.ElementTree(rss)
        rss_path = self.site.output_dir / 'rss.xml'
        
        # Format XML with indentation
        self._indent(rss)
        
        # Write atomically using context manager
        try:
            with AtomicFile(rss_path, 'wb') as f:
                tree.write(f, encoding='utf-8', xml_declaration=True)
            
            self.logger.info("rss_generation_complete",
                           rss_path=str(rss_path),
                           items_included=min(20, len(sorted_pages)),
                           total_pages_with_dates=len(pages_with_dates))
            
            print(f"   ├─ RSS feed ✓")
        except Exception as e:
            self.logger.error("rss_generation_failed",
                            rss_path=str(rss_path),
                            error=str(e),
                            error_type=type(e).__name__)
            raise
    
    def _indent(self, elem: ET.Element, level: int = 0) -> None:
        """
        Add indentation to XML for readability.
        
        Args:
            elem: XML element to indent
            level: Current indentation level
        """
        indent = "\n" + "  " * level
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for child in elem:
                self._indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent

