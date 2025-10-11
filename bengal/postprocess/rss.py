"""
RSS feed generation.
"""

import xml.etree.ElementTree as ET
from typing import Any

from bengal.utils.logger import get_logger


class RSSGenerator:
    """
    Generates RSS feed for the site.

    Creates an rss.xml file with the 20 most recent pages that have dates,
    enabling readers to subscribe to site updates via RSS readers.

    Features:
    - Includes title, link, description for each item
    - Sorted by date (newest first)
    - Limited to 20 most recent items
    - RFC 822 date formatting
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
        """
        Generate and write rss.xml to output directory.

        Filters pages with dates, sorts by date (newest first), limits to 20 items,
        and writes RSS feed atomically to prevent corruption.

        Raises:
            Exception: If RSS generation or file writing fails
        """
        # Per-locale generation (prefix strategy) or single feed
        i18n = self.site.config.get('i18n', {}) or {}
        strategy = i18n.get('strategy', 'none')
        default_lang = i18n.get('default_language', 'en')
        default_in_subdir = bool(i18n.get('default_in_subdir', False))
        languages_cfg = i18n.get('languages') or []
        lang_codes = []
        for entry in languages_cfg:
            if isinstance(entry, dict) and 'code' in entry:
                lang_codes.append(entry['code'])
            elif isinstance(entry, str):
                lang_codes.append(entry)
        if default_lang and default_lang not in lang_codes:
            lang_codes.append(default_lang)
        if not lang_codes:
            lang_codes = [default_lang]

        # Build one RSS per language (for prefix strategy) or single if no i18n
        for code in sorted(set(lang_codes)):
            pages_with_dates = [p for p in self.site.pages if p.date and (strategy == 'none' or getattr(p, 'lang', default_lang) == code)]
            sorted_pages = sorted(pages_with_dates, key=lambda p: p.date, reverse=True)

            self.logger.info("rss_generation_start",
                            lang=code,
                            total_pages=len(self.site.pages),
                            pages_with_dates=len(pages_with_dates),
                            rss_limit=min(20, len(sorted_pages)))

            # Create root element
            rss = ET.Element('rss')
            rss.set('version', '2.0')
            channel = ET.SubElement(rss, 'channel')

            # Channel metadata
            title = self.site.config.get('title', 'Bengal Site')
            baseurl = self.site.config.get('baseurl', '')
            description = self.site.config.get('description', f'{title} RSS Feed')
            ET.SubElement(channel, 'title').text = title
            ET.SubElement(channel, 'link').text = baseurl
            ET.SubElement(channel, 'description').text = description

            # Items
            for page in sorted_pages[:20]:
                item = ET.SubElement(channel, 'item')
                ET.SubElement(item, 'title').text = page.title

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

                if 'description' in page.metadata:
                    desc_text = page.metadata['description']
                else:
                    content = page.content[:200] + '...' if len(page.content) > 200 else page.content
                    desc_text = content
                ET.SubElement(item, 'description').text = desc_text

                if page.date:
                    pubdate = page.date.strftime('%a, %d %b %Y %H:%M:%S +0000')
                    ET.SubElement(item, 'pubDate').text = pubdate

            # Write per-language RSS
            from bengal.utils.atomic_write import AtomicFile
            tree = ET.ElementTree(rss)
            if strategy == 'prefix' and (default_in_subdir or code != default_lang):
                rss_path = self.site.output_dir / code / 'rss.xml'
            else:
                # For non-i18n or default language without subdir
                rss_path = self.site.output_dir / 'rss.xml' if code == default_lang else self.site.output_dir / code / 'rss.xml'

            # Ensure directory exists
            rss_path.parent.mkdir(parents=True, exist_ok=True)
            self._indent(rss)
            try:
                with AtomicFile(rss_path, 'wb') as f:
                    tree.write(f, encoding='utf-8', xml_declaration=True)
                self.logger.info("rss_generation_complete",
                               lang=code,
                               rss_path=str(rss_path),
                               items_included=min(20, len(sorted_pages)),
                               total_pages_with_dates=len(pages_with_dates))
            except Exception as e:
                self.logger.error("rss_generation_failed",
                                lang=code,
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
        elif level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent

