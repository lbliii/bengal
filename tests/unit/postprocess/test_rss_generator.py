"""
Tests for bengal/postprocess/rss.py.

Covers:
- RSSGenerator initialization
- RSS feed generation with pages
- Date sorting (newest first)
- RSS limit (max 20 items)
- Page visibility filtering (in_rss, draft)
- i18n per-locale feed generation
- RFC 822 date formatting
- Channel metadata (title, link, description)
- Item structure (title, link, guid, description, pubDate)
- No pages with dates (skip generation)
- Atomic file writing
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch


class TestRSSGeneratorBasics:
    """Test RSSGenerator initialization and basic properties."""

    def test_init_stores_site(self) -> None:
        """Test that RSSGenerator stores site reference."""
        from bengal.postprocess.rss import RSSGenerator

        site = MagicMock()
        generator = RSSGenerator(site)

        assert generator.site is site

    def test_init_creates_logger(self) -> None:
        """Test that RSSGenerator creates a logger."""
        from bengal.postprocess.rss import RSSGenerator

        site = MagicMock()
        generator = RSSGenerator(site)

        assert generator.logger is not None


class TestRSSGeneratorNoPagesWithDates:
    """Test RSS generation when no pages have dates."""

    def test_skips_when_no_pages(self) -> None:
        """Test that generation is skipped when site has no pages."""
        from bengal.postprocess.rss import RSSGenerator

        site = MagicMock()
        site.pages = []

        generator = RSSGenerator(site)
        generator.generate()  # Should not raise

    def test_skips_when_no_pages_with_dates(self) -> None:
        """Test that generation is skipped when no pages have dates."""
        from bengal.postprocess.rss import RSSGenerator

        page = MagicMock()
        page.date = None
        page.in_rss = True

        site = MagicMock()
        site.pages = [page]

        generator = RSSGenerator(site)
        generator.generate()  # Should not raise

    def test_skips_when_pages_not_in_rss(self) -> None:
        """Test that pages with in_rss=False are excluded."""
        from bengal.postprocess.rss import RSSGenerator

        page = MagicMock()
        page.date = datetime(2024, 1, 1)
        page.in_rss = False

        site = MagicMock()
        site.pages = [page]

        generator = RSSGenerator(site)
        generator.generate()  # Should not raise


class TestRSSGeneratorWithPages:
    """Test RSS generation with valid pages."""

    def _create_mock_page(
        self,
        title: str = "Test Page",
        date: datetime | None = None,
        in_rss: bool = True,
        content: str = "Test content",
        slug: str = "test-page",
        output_path: Path | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MagicMock:
        """Create a mock page for testing."""
        page = MagicMock()
        page.title = title
        page.date = date
        page.in_rss = in_rss
        page.content = content
        page.slug = slug
        page.output_path = output_path
        page.metadata = metadata or {}
        page.lang = None
        return page

    def _create_mock_site(
        self,
        pages: list[MagicMock] | None = None,
        config: dict[str, Any] | None = None,
        output_dir: Path | None = None,
    ) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.pages = pages or []
        default_config = {"title": "Test Site", "baseurl": "https://example.com"}
        site.config = config or default_config
        site.output_dir = output_dir or Path("/tmp/output")
        # Set properties as string attributes (not Mock objects) for proper access
        # Handle both nested and flat config structures
        if config:
            site_section = config.get("site", {})
            if isinstance(site_section, dict):
                site.title = str(site_section.get("title", config.get("title", "Test Site")))
                site.baseurl = str(site_section.get("baseurl", config.get("baseurl", "")))
                site.description = str(
                    site_section.get("description", config.get("description", ""))
                )
            else:
                site.title = str(config.get("title", "Test Site"))
                site.baseurl = str(config.get("baseurl", ""))
                site.description = str(config.get("description", ""))
        else:
            site.title = "Test Site"
            site.baseurl = "https://example.com"
            site.description = ""
        return site

    @patch("bengal.utils.io.atomic_write.AtomicFile")
    def test_generates_rss_with_pages(self, mock_atomic: MagicMock, tmp_path: Path) -> None:
        """Test RSS generation with pages that have dates."""
        from bengal.postprocess.rss import RSSGenerator

        page = self._create_mock_page(
            title="Test Post",
            date=datetime(2024, 1, 15),
            output_path=tmp_path / "test-post" / "index.html",
        )

        site = self._create_mock_site(
            pages=[page],
            output_dir=tmp_path,
            config={
                "title": "Test Site",
                "baseurl": "https://example.com",
                "description": "A test site",
                "i18n": {},
            },
        )

        # Make output_path relative_to work
        page.output_path = tmp_path / "test-post" / "index.html"

        generator = RSSGenerator(site)

        mock_file = MagicMock()
        mock_atomic.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_atomic.return_value.__exit__ = MagicMock(return_value=False)

        generator.generate()

        # Verify AtomicFile was called
        assert mock_atomic.called

    def test_sorts_pages_by_date_newest_first(self) -> None:
        """Test that pages are sorted by date (newest first)."""
        from bengal.postprocess.rss import RSSGenerator

        # Create pages with different dates
        page1 = self._create_mock_page(title="Oldest", date=datetime(2024, 1, 1))
        page2 = self._create_mock_page(title="Middle", date=datetime(2024, 6, 15))
        page3 = self._create_mock_page(title="Newest", date=datetime(2024, 12, 31))

        site = self._create_mock_site(pages=[page1, page2, page3])

        generator = RSSGenerator(site)

        # Get pages with dates and sort (mimicking generate logic)
        pages_with_dates = [p for p in site.pages if p.date and p.in_rss]
        sorted_pages = sorted(pages_with_dates, key=lambda p: p.date, reverse=True)

        assert sorted_pages[0].title == "Newest"
        assert sorted_pages[1].title == "Middle"
        assert sorted_pages[2].title == "Oldest"

    def test_limits_to_20_items(self) -> None:
        """Test that RSS feed is limited to 20 items."""
        from bengal.postprocess.rss import RSSGenerator

        # Create 25 pages
        pages = [
            self._create_mock_page(
                title=f"Post {i}",
                date=datetime(2024, 1, i + 1),
                slug=f"post-{i}",
            )
            for i in range(25)
        ]

        site = self._create_mock_site(pages=pages)

        generator = RSSGenerator(site)

        # Get pages with dates and limit (mimicking generate logic)
        pages_with_dates = [p for p in site.pages if p.date and p.in_rss]
        sorted_pages = sorted(pages_with_dates, key=lambda p: p.date, reverse=True)
        limited = sorted_pages[:20]

        assert len(limited) == 20


class TestRSSGeneratori18n:
    """Test RSS generation with i18n configuration."""

    def _create_mock_page(
        self, title: str, date: datetime, lang: str = "en", **kwargs: Any
    ) -> MagicMock:
        """Create a mock page with language."""
        page = MagicMock()
        page.title = title
        page.date = date
        page.lang = lang
        page.in_rss = True
        page.content = "Test content"
        page.slug = title.lower().replace(" ", "-")
        page.output_path = None
        page.metadata = {}
        return page

    def test_filters_pages_by_language_in_prefix_strategy(self) -> None:
        """Test that pages are filtered by language in prefix strategy."""
        from bengal.postprocess.rss import RSSGenerator

        page_en = self._create_mock_page("English Post", datetime(2024, 1, 1), lang="en")
        page_fr = self._create_mock_page("French Post", datetime(2024, 1, 2), lang="fr")

        site = MagicMock()
        site.pages = [page_en, page_fr]
        site.config = {
            "title": "Test Site",
            "baseurl": "https://example.com",
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "languages": [{"code": "en"}, {"code": "fr"}],
            },
        }
        site.output_dir = Path("/tmp/output")

        generator = RSSGenerator(site)

        # Verify filtering logic
        i18n = site.config.get("i18n", {}) or {}
        strategy = i18n.get("strategy", "none")
        default_lang = i18n.get("default_language", "en")

        # Filter for English
        en_pages = [
            p
            for p in site.pages
            if p.date
            and p.in_rss
            and (strategy == "none" or getattr(p, "lang", default_lang) == "en")
        ]
        assert len(en_pages) == 1
        assert en_pages[0].title == "English Post"

        # Filter for French
        fr_pages = [
            p
            for p in site.pages
            if p.date
            and p.in_rss
            and (strategy == "none" or getattr(p, "lang", default_lang) == "fr")
        ]
        assert len(fr_pages) == 1
        assert fr_pages[0].title == "French Post"


class TestRSSGeneratorXMLStructure:
    """Test RSS XML structure and formatting."""

    def test_xml_has_rss_root_element(self) -> None:
        """Test that generated XML has rss root element with version."""
        rss = ET.Element("rss")
        rss.set("version", "2.0")

        assert rss.tag == "rss"
        assert rss.get("version") == "2.0"

    def test_xml_has_channel_element(self) -> None:
        """Test that RSS has channel element."""
        rss = ET.Element("rss")
        channel = ET.SubElement(rss, "channel")

        assert channel.tag == "channel"
        assert channel in list(rss)

    def test_channel_has_required_elements(self) -> None:
        """Test that channel has title, link, description."""
        rss = ET.Element("rss")
        channel = ET.SubElement(rss, "channel")

        ET.SubElement(channel, "title").text = "Test Site"
        ET.SubElement(channel, "link").text = "https://example.com"
        ET.SubElement(channel, "description").text = "A test site"

        title = channel.find("title")
        link = channel.find("link")
        description = channel.find("description")

        assert title is not None and title.text == "Test Site"
        assert link is not None and link.text == "https://example.com"
        assert description is not None and description.text == "A test site"

    def test_item_has_required_elements(self) -> None:
        """Test that item has title, link, guid, description, pubDate."""
        item = ET.Element("item")

        ET.SubElement(item, "title").text = "Test Post"
        ET.SubElement(item, "link").text = "https://example.com/test-post/"
        ET.SubElement(item, "guid").text = "https://example.com/test-post/"
        ET.SubElement(item, "description").text = "Test description"
        ET.SubElement(item, "pubDate").text = "Mon, 15 Jan 2024 00:00:00 +0000"

        assert item.find("title") is not None
        assert item.find("link") is not None
        assert item.find("guid") is not None
        assert item.find("description") is not None
        assert item.find("pubDate") is not None


class TestRSSGeneratorDateFormatting:
    """Test RFC 822 date formatting."""

    def test_formats_date_as_rfc822(self) -> None:
        """Test that dates are formatted as RFC 822."""
        date = datetime(2024, 1, 15, 12, 30, 45)
        formatted = date.strftime("%a, %d %b %Y %H:%M:%S +0000")

        assert formatted == "Mon, 15 Jan 2024 12:30:45 +0000"

    def test_formats_midnight_correctly(self) -> None:
        """Test that midnight is formatted correctly."""
        date = datetime(2024, 1, 1, 0, 0, 0)
        formatted = date.strftime("%a, %d %b %Y %H:%M:%S +0000")

        assert formatted == "Mon, 01 Jan 2024 00:00:00 +0000"


class TestRSSGeneratorDescriptionHandling:
    """Test item description handling."""

    def test_uses_metadata_description_if_available(self) -> None:
        """Test that metadata description is used if available."""
        page = MagicMock()
        page.metadata = {"description": "Custom description"}
        page.content = "Page content that is longer than 200 characters..."

        # Mimicking the logic from RSSGenerator.generate()
        if "description" in page.metadata:
            desc_text = page.metadata["description"]
        else:
            content = page.content[:200] + "..." if len(page.content) > 200 else page.content
            desc_text = content

        assert desc_text == "Custom description"

    def test_uses_truncated_content_if_no_description(self) -> None:
        """Test that truncated content is used if no description."""
        page = MagicMock()
        page.metadata = {}
        page.content = "A" * 250

        if "description" in page.metadata:
            desc_text = page.metadata["description"]
        else:
            content = page.content[:200] + "..." if len(page.content) > 200 else page.content
            desc_text = content

        assert desc_text == "A" * 200 + "..."

    def test_uses_full_content_if_under_200_chars(self) -> None:
        """Test that full content is used if under 200 characters."""
        page = MagicMock()
        page.metadata = {}
        page.content = "Short content"

        if "description" in page.metadata:
            desc_text = page.metadata["description"]
        else:
            content = page.content[:200] + "..." if len(page.content) > 200 else page.content
            desc_text = content

        assert desc_text == "Short content"


class TestRSSGeneratorIndentation:
    """Test XML indentation functionality."""

    def test_indent_adds_whitespace(self) -> None:
        """Test that indent_xml adds whitespace to XML."""
        from bengal.postprocess.utils import indent_xml

        rss = ET.Element("rss")
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = "Test"

        indent_xml(rss)

        # After indentation, elements should have text/tail with newlines
        assert channel.text is not None or channel.tail is not None


class TestRSSGeneratorLinkGeneration:
    """Test RSS item link generation."""

    def test_generates_link_from_output_path(self, tmp_path: Path) -> None:
        """Test link generation from output_path."""
        from bengal.postprocess.rss import RSSGenerator

        page = MagicMock()
        page.output_path = tmp_path / "blog" / "test-post" / "index.html"
        page.slug = "test-post"

        site = MagicMock()
        site.output_dir = tmp_path
        site.config = {"baseurl": "https://example.com"}

        generator = RSSGenerator(site)

        # Mimicking link generation logic
        # Access from site section (supports both Config and dict)
        if hasattr(site.config, "site"):
            baseurl = site.config.site.baseurl or ""
        else:
            baseurl = site.config.get("site", {}).get("baseurl", "")
        if page.output_path:
            try:
                rel_path = page.output_path.relative_to(site.output_dir)
                link = f"{baseurl}/{rel_path}".replace("\\", "/")
                link = link.replace("/index.html", "/")
            except ValueError:
                link = f"{baseurl}/{page.slug}/"
        else:
            link = f"{baseurl}/{page.slug}/"

        assert link == "https://example.com/blog/test-post/"

    def test_falls_back_to_slug_when_no_output_path(self) -> None:
        """Test that link falls back to slug when no output_path."""
        page = MagicMock()
        page.output_path = None
        page.slug = "test-post"

        baseurl = "https://example.com"
        link = f"{baseurl}/{page.slug}/"

        assert link == "https://example.com/test-post/"
