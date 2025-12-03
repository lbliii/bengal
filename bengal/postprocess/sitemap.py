"""
Sitemap generation for SEO.
"""


from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from bengal.utils.logger import get_logger


class SitemapGenerator:
    """
    Generates XML sitemap for SEO.

    Creates a sitemap.xml file listing all pages with metadata like:
    - URL location
    - Last modified date
    - Change frequency
    - Priority

    The sitemap helps search engines discover and index site content.
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
        """
        Generate and write sitemap.xml to output directory.

        Iterates through all pages, creates XML entries with URLs and metadata,
        and writes the sitemap atomically to prevent corruption.

        If no pages exist, logs info and skips generation (no empty sitemap file).

        Raises:
            Exception: If sitemap generation or file writing fails
        """
        # Skip if no pages (empty site)
        if not self.site.pages:
            self.logger.info(
                "sitemap_skipped",
                reason="no_pages",
                hint="Site has no pages to include in sitemap",
            )
            return

        self.logger.info("sitemap_generation_start", total_pages=len(self.site.pages))

        # Create root element with xhtml namespace for hreflang alternates
        urlset = ET.Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        urlset.set("xmlns:xhtml", "http://www.w3.org/1999/xhtml")

        baseurl = self.site.config.get("baseurl", "")

        # Add each page to sitemap
        included_count = 0
        skipped_count = 0

        for page in self.site.pages:
            # Skip pages that shouldn't be in sitemap (hidden, visibility.sitemap=false, drafts)
            if not page.in_sitemap:
                skipped_count += 1
                continue

            url_elem = ET.SubElement(urlset, "url")

            # Get page URL
            if page.output_path:
                try:
                    rel_path = page.output_path.relative_to(self.site.output_dir)
                    loc = f"{baseurl}/{rel_path}".replace("\\", "/")
                except ValueError:
                    skipped_count += 1
                    continue
            else:
                loc = f"{baseurl}/{page.slug}/"

            # Remove /index.html for cleaner URLs
            loc = loc.replace("/index.html", "/")

            ET.SubElement(url_elem, "loc").text = loc

            # Add hreflang alternates when translation_key present
            try:
                if getattr(page, "translation_key", None):
                    key = page.translation_key
                    # Collect alternates
                    seen = set()
                    for p in self.site.pages:
                        if getattr(p, "translation_key", None) == key and p.output_path:
                            try:
                                rel = p.output_path.relative_to(self.site.output_dir)
                                href = f"{baseurl}/{rel}".replace("\\", "/")
                                href = href.replace("/index.html", "/")
                            except ValueError:
                                # Skip pages not under output_dir
                                continue
                            lang = getattr(p, "lang", None) or self.site.config.get("i18n", {}).get(
                                "default_language", "en"
                            )
                            if (lang, href) in seen:
                                continue
                            link = ET.SubElement(url_elem, "{http://www.w3.org/1999/xhtml}link")
                            link.set("rel", "alternate")
                            link.set("hreflang", lang)
                            link.set("href", href)
                            seen.add((lang, href))
                    # Add x-default if default language exists among alternates
                    default_lang = self.site.config.get("i18n", {}).get("default_language", "en")
                    for child in list(url_elem):
                        if child.tag.endswith("link") and child.get("hreflang") == default_lang:
                            link = ET.SubElement(url_elem, "{http://www.w3.org/1999/xhtml}link")
                            link.set("rel", "alternate")
                            link.set("hreflang", "x-default")
                            link.set("href", child.get("href"))
                            break
            except Exception:
                # Keep sitemap resilient
                pass
            included_count += 1

            # Add lastmod if available
            if page.date:
                lastmod = page.date.strftime("%Y-%m-%d")
                ET.SubElement(url_elem, "lastmod").text = lastmod

            # Add default priority and changefreq
            ET.SubElement(url_elem, "changefreq").text = "weekly"
            ET.SubElement(url_elem, "priority").text = "0.5"

        # Write sitemap to file atomically (crash-safe)
        from bengal.utils.atomic_write import AtomicFile

        tree = ET.ElementTree(urlset)
        sitemap_path = self.site.output_dir / "sitemap.xml"

        # Format XML with indentation
        self._indent(urlset)

        # Write atomically using context manager
        try:
            with AtomicFile(sitemap_path, "wb") as f:
                tree.write(f, encoding="utf-8", xml_declaration=True)

            self.logger.info(
                "sitemap_generation_complete",
                sitemap_path=str(sitemap_path),
                pages_included=included_count,
                pages_skipped=skipped_count,
                total_pages=len(self.site.pages),
            )

            # Detailed output removed - postprocess phase summary is sufficient
            # Individual task output clutters the build log
        except Exception as e:
            self.logger.error(
                "sitemap_generation_failed",
                sitemap_path=str(sitemap_path),
                error=str(e),
                error_type=type(e).__name__,
            )
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
        elif level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent
