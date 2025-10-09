"""
Sitemap generation for SEO.
"""

from pathlib import Path
from typing import Any
from datetime import datetime
import xml.etree.ElementTree as ET

from bengal.utils.logger import get_logger


class SitemapGenerator:
    """
    Generates XML sitemap for the site.
    """
    
    def __init__(self, site: Any) -> None:
        """
        Initialize sitemap generator.
        
        Args:
            site: Site instance
        """
        self.site = site
        self.logger = get_logger(__name__)
    
    def generate(self) -> None:
        """Generate and write sitemap.xml."""
        self.logger.info("sitemap_generation_start",
                        total_pages=len(self.site.pages))
        
        # Create root element
        urlset = ET.Element('urlset')
        urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
        
        baseurl = self.site.config.get('baseurl', '')
        
        # Add each page to sitemap
        included_count = 0
        skipped_count = 0
        
        for page in self.site.pages:
            url_elem = ET.SubElement(urlset, 'url')
            
            # Get page URL
            if page.output_path:
                try:
                    rel_path = page.output_path.relative_to(self.site.output_dir)
                    loc = f"{baseurl}/{rel_path}".replace('\\', '/')
                except ValueError:
                    skipped_count += 1
                    continue
            else:
                loc = f"{baseurl}/{page.slug}/"
            
            # Remove /index.html for cleaner URLs
            loc = loc.replace('/index.html', '/')
            
            ET.SubElement(url_elem, 'loc').text = loc
            included_count += 1
            
            # Add lastmod if available
            if page.date:
                lastmod = page.date.strftime('%Y-%m-%d')
                ET.SubElement(url_elem, 'lastmod').text = lastmod
            
            # Add default priority and changefreq
            ET.SubElement(url_elem, 'changefreq').text = 'weekly'
            ET.SubElement(url_elem, 'priority').text = '0.5'
        
        # Write sitemap to file atomically (crash-safe)
        from bengal.utils.atomic_write import AtomicFile
        
        tree = ET.ElementTree(urlset)
        sitemap_path = self.site.output_dir / 'sitemap.xml'
        
        # Format XML with indentation
        self._indent(urlset)
        
        # Write atomically using context manager
        try:
            with AtomicFile(sitemap_path, 'wb') as f:
                tree.write(f, encoding='utf-8', xml_declaration=True)
            
            self.logger.info("sitemap_generation_complete",
                           sitemap_path=str(sitemap_path),
                           pages_included=included_count,
                           pages_skipped=skipped_count,
                           total_pages=len(self.site.pages))
            
            # Detailed output removed - postprocess phase summary is sufficient
            # Individual task output clutters the build log
        except Exception as e:
            self.logger.error("sitemap_generation_failed",
                            sitemap_path=str(sitemap_path),
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

