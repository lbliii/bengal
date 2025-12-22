"""
Sitemap generation for SEO.

Generates XML sitemap files for search engine discovery and indexing. Creates
sitemap.xml with page URLs, modification dates, change frequencies, and priorities.
Supports sitemap index files for large sites.

Key Concepts:
    - XML sitemap: Standard XML format for search engine discovery
    - Page metadata: Last modified dates, change frequencies, priorities
    - Sitemap index: Index file for multiple sitemap files (large sites)
    - SEO optimization: Helps search engines discover and index content

Related Modules:
    - bengal.orchestration.postprocess: Post-processing orchestration
    - bengal.core.site: Site container with pages
    - bengal.core.page: Page objects with metadata

See Also:
    - bengal/postprocess/sitemap.py:SitemapGenerator for sitemap generation
    - https://www.sitemaps.org/: Sitemap protocol specification
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.output import OutputCollector


class SitemapGenerator:
    """
    Generates XML sitemap for SEO and search engine discovery.

    Creates sitemap.xml files listing all pages with metadata for search engines.
    Supports sitemap index files for large sites and i18n alternate language links.

    Creation:
        Direct instantiation: SitemapGenerator(site)
            - Created by PostprocessOrchestrator for sitemap generation
            - Requires Site instance with rendered pages

    Attributes:
        site: Site instance with pages and configuration
        logger: Logger instance for sitemap generation events

    Relationships:
        - Used by: PostprocessOrchestrator for sitemap generation
        - Uses: Site for page access and configuration

    Features:
        - URL location with baseurl support
        - Last modified dates from page metadata
        - Change frequency and priority metadata
        - i18n alternate language links (hreflang)
        - Sitemap index support for large sites

    Examples:
        generator = SitemapGenerator(site)
        generator.generate()  # Writes sitemap.xml to output directory
    """

    def __init__(self, site: Any, collector: OutputCollector | None = None) -> None:
        """
        Initialize sitemap generator.

        Args:
            site: Site instance
            collector: Optional output collector for hot reload tracking
        """
        self.site = site
        self.logger = get_logger(__name__)
        self._collector = collector

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

        # Build translation index once: O(n) instead of O(n²) for hreflang lookups
        translation_index: dict[str, list[Any]] = {}
        for page in self.site.pages:
            key = getattr(page, "translation_key", None)
            if key:
                translation_index.setdefault(key, []).append(page)

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
                    # Collect alternates using pre-built index: O(1) lookup
                    seen = set()
                    for p in translation_index.get(key, []):
                        if p.output_path:
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
                            default_href: str | None = child.get("href")
                            if default_href is not None:
                                link = ET.SubElement(url_elem, "{http://www.w3.org/1999/xhtml}link")
                                link.set("rel", "alternate")
                                link.set("hreflang", "x-default")
                                link.set("href", default_href)
                                break
            except Exception as e:
                # Keep sitemap resilient
                self.logger.debug(
                    "sitemap_hreflang_processing_failed",
                    page_url=getattr(page, "_path", None),
                    error=str(e),
                    error_type=type(e).__name__,
                    action="skipping_hreflang",
                )
                pass
            included_count += 1

            # Add lastmod if available
            if page.date:
                lastmod = page.date.strftime("%Y-%m-%d")
                ET.SubElement(url_elem, "lastmod").text = lastmod

            # Add default priority and changefreq
            # Version-aware: older versions get lower priority
            priority = self._get_version_priority(page)
            ET.SubElement(url_elem, "changefreq").text = "weekly"
            ET.SubElement(url_elem, "priority").text = priority

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

            # Record output for hot reload tracking
            if self._collector:
                from bengal.core.output import OutputType

                self._collector.record(sitemap_path, OutputType.XML, phase="postprocess")

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

    def _get_version_priority(self, page: Any) -> str:
        """
        Get sitemap priority for a page based on version.

        Latest version pages get priority 0.8.
        Older version pages get priority 0.3 (lower but still indexed).
        Non-versioned pages get default priority 0.5.

        Args:
            page: Page object

        Returns:
            Priority string (0.0-1.0)
        """
        # Check if versioning is enabled
        if not getattr(self.site, "versioning_enabled", False):
            return "0.5"

        version_config = getattr(self.site, "version_config", None)
        if not version_config:
            return "0.5"

        # Get page version
        page_version = getattr(page, "version", None)
        if not page_version:
            # Non-versioned page
            return "0.5"

        # Get version object
        version = version_config.get_version(page_version)
        if not version:
            return "0.5"

        # Latest version gets higher priority
        if version.latest:
            return "0.8"
        else:
            # Older versions get lower priority but still indexed
            return "0.3"

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
