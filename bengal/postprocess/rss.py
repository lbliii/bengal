"""
RSS feed generation for content syndication.

Generates RSS/Atom feeds for blog content, enabling readers to subscribe to
site updates via RSS readers. Creates rss.xml with recent pages sorted by date.

Key Concepts:
    - RSS format: Standard RSS 2.0 format for content syndication
    - Recent pages: Limited to 20 most recent pages with dates
    - Date sorting: Pages sorted by date (newest first)
    - RFC 822 dates: Standard date formatting for RSS feeds

Related Modules:
    - bengal.orchestration.postprocess: Post-processing orchestration
    - bengal.core.site: Site container with pages
    - bengal.core.page: Page objects with dates

See Also:
    - bengal/postprocess/rss.py:RSSGenerator for RSS generation
    - https://www.rssboard.org/rss-specification: RSS 2.0 specification
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.output import OutputCollector


class RSSGenerator:
    """
    Generates RSS/Atom feeds for content syndication.

    Creates rss.xml files with recent pages sorted by date, enabling readers
    to subscribe to site updates via RSS readers. Supports i18n per-locale feeds
    and respects page visibility settings.

    Creation:
        Direct instantiation: RSSGenerator(site)
            - Created by PostprocessOrchestrator for RSS generation
            - Requires Site instance with rendered pages

    Attributes:
        site: Site instance with pages and configuration
        logger: Logger instance for RSS generation events

    Relationships:
        - Used by: PostprocessOrchestrator for RSS generation
        - Uses: Site for page access and configuration

    Features:
        - Includes title, link, description for each item
        - Sorted by date (newest first)
        - Limited to 20 most recent items
        - RFC 822 date formatting
        - i18n per-locale feeds (if i18n enabled)
        - Respects page visibility (draft, rss visibility)

    Examples:
        generator = RSSGenerator(site)
        generator.generate()  # Writes rss.xml to output directory
    """

    def __init__(self, site: Any, collector: OutputCollector | None = None) -> None:
        """
        Initialize RSS generator.

        Args:
            site: Site instance
            collector: Optional output collector for hot reload tracking
        """
        self.site = site
        self.logger = get_logger(__name__)
        self._collector = collector

    def generate(self) -> None:
        """
        Generate and write rss.xml to output directory.

        Filters pages with dates, sorts by date (newest first), limits to 20 items,
        and writes RSS feed atomically to prevent corruption.

        If no pages with dates exist, logs info and skips generation.

        Raises:
            Exception: If RSS generation or file writing fails
        """
        # Check for any pages with dates first (also filter by visibility)
        # in_rss checks visibility.rss AND not draft
        pages_with_dates = [p for p in self.site.pages if p.date and p.in_rss]
        if not pages_with_dates:
            self.logger.info(
                "rss_skipped",
                reason="no_pages_with_dates",
                total_pages=len(self.site.pages),
                hint="No pages have dates set. Add 'date:' to frontmatter to include in RSS feed.",
            )
            return

        # Per-locale generation (prefix strategy) or single feed
        i18n = self.site.config.get("i18n", {}) or {}
        strategy = i18n.get("strategy", "none")
        default_lang = i18n.get("default_language", "en")
        default_in_subdir = bool(i18n.get("default_in_subdir", False))
        languages_cfg = i18n.get("languages") or []
        lang_codes = []
        for entry in languages_cfg:
            if isinstance(entry, dict) and "code" in entry:
                lang_codes.append(entry["code"])
            elif isinstance(entry, str):
                lang_codes.append(entry)
        if default_lang and default_lang not in lang_codes:
            lang_codes.append(default_lang)
        if not lang_codes:
            lang_codes = [default_lang]

        # Build one RSS per language (for prefix strategy) or single if no i18n
        for code in sorted(set(lang_codes)):
            pages_with_dates = [
                p
                for p in self.site.pages
                if p.date
                and p.in_rss
                and (strategy == "none" or getattr(p, "lang", default_lang) == code)
            ]
            sorted_pages = sorted(pages_with_dates, key=lambda p: p.date, reverse=True)

            self.logger.info(
                "rss_generation_start",
                lang=code,
                total_pages=len(self.site.pages),
                pages_with_dates=len(pages_with_dates),
                rss_limit=min(20, len(sorted_pages)),
            )

            # Create root element
            rss = ET.Element("rss")
            rss.set("version", "2.0")
            channel = ET.SubElement(rss, "channel")

            # Channel metadata
            title = self.site.config.get("title", "Bengal Site")
            baseurl = self.site.config.get("baseurl", "")
            description = self.site.config.get("description", f"{title} RSS Feed")
            ET.SubElement(channel, "title").text = title
            ET.SubElement(channel, "link").text = baseurl
            ET.SubElement(channel, "description").text = description

            # Items
            for page in sorted_pages[:20]:
                item = ET.SubElement(channel, "item")
                ET.SubElement(item, "title").text = page.title

                if page.output_path:
                    try:
                        rel_path = page.output_path.relative_to(self.site.output_dir)
                        link = f"{baseurl}/{rel_path}".replace("\\", "/")
                        link = link.replace("/index.html", "/")
                    except ValueError:
                        link = f"{baseurl}/{page.slug}/"
                else:
                    link = f"{baseurl}/{page.slug}/"
                ET.SubElement(item, "link").text = link
                ET.SubElement(item, "guid").text = link

                if "description" in page.metadata:
                    desc_text = page.metadata["description"]
                else:
                    content = (
                        page.content[:200] + "..." if len(page.content) > 200 else page.content
                    )
                    desc_text = content
                ET.SubElement(item, "description").text = desc_text

                if page.date:
                    pubdate = page.date.strftime("%a, %d %b %Y %H:%M:%S +0000")
                    ET.SubElement(item, "pubDate").text = pubdate

            # Write per-language RSS
            from bengal.utils.atomic_write import AtomicFile

            tree = ET.ElementTree(rss)
            if strategy == "prefix" and (default_in_subdir or code != default_lang):
                rss_path = self.site.output_dir / code / "rss.xml"
            else:
                # For non-i18n or default language without subdir
                rss_path = (
                    self.site.output_dir / "rss.xml"
                    if code == default_lang
                    else self.site.output_dir / code / "rss.xml"
                )

            # Ensure directory exists
            rss_path.parent.mkdir(parents=True, exist_ok=True)
            self._indent(rss)
            try:
                with AtomicFile(rss_path, "wb") as f:
                    tree.write(f, encoding="utf-8", xml_declaration=True)

                # Record output for hot reload tracking
                if self._collector:
                    from bengal.core.output import OutputType

                    self._collector.record(rss_path, OutputType.XML, phase="postprocess")

                self.logger.info(
                    "rss_generation_complete",
                    lang=code,
                    rss_path=str(rss_path),
                    items_included=min(20, len(sorted_pages)),
                    total_pages_with_dates=len(pages_with_dates),
                )
            except Exception as e:
                self.logger.error(
                    "rss_generation_failed",
                    lang=code,
                    rss_path=str(rss_path),
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
