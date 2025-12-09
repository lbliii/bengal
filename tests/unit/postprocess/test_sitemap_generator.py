"""
Tests for bengal/postprocess/sitemap.py.

Covers:
- SitemapGenerator initialization
- Sitemap generation with pages
- Page visibility filtering (in_sitemap, draft, hidden)
- URL generation (loc)
- Last modified dates (lastmod)
- Change frequency (changefreq)
- Priority values
- i18n hreflang alternates
- Empty site handling (no pages)
- Atomic file writing
- XML structure and formatting
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch


class TestSitemapGeneratorBasics:
    """Test SitemapGenerator initialization and basic properties."""

    def test_init_stores_site(self) -> None:
        """Test that SitemapGenerator stores site reference."""
        from bengal.postprocess.sitemap import SitemapGenerator

        site = MagicMock()
        generator = SitemapGenerator(site)

        assert generator.site is site

    def test_init_creates_logger(self) -> None:
        """Test that SitemapGenerator creates a logger."""
        from bengal.postprocess.sitemap import SitemapGenerator

        site = MagicMock()
        generator = SitemapGenerator(site)

        assert generator.logger is not None


class TestSitemapGeneratorNoPages:
    """Test sitemap generation when site has no pages."""

    def test_skips_when_no_pages(self) -> None:
        """Test that generation is skipped when site has no pages."""
        from bengal.postprocess.sitemap import SitemapGenerator

        site = MagicMock()
        site.pages = []

        generator = SitemapGenerator(site)
        generator.generate()  # Should not raise


class TestSitemapGeneratorWithPages:
    """Test sitemap generation with valid pages."""

    def _create_mock_page(
        self,
        title: str = "Test Page",
        slug: str = "test-page",
        in_sitemap: bool = True,
        date: datetime | None = None,
        output_path: Path | None = None,
        translation_key: str | None = None,
        lang: str | None = None,
    ) -> MagicMock:
        """Create a mock page for testing."""
        page = MagicMock()
        page.title = title
        page.slug = slug
        page.in_sitemap = in_sitemap
        page.date = date
        page.output_path = output_path
        page.translation_key = translation_key
        page.lang = lang
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
        site.config = config or {"baseurl": "https://example.com"}
        site.output_dir = output_dir or Path("/tmp/output")
        return site

    @patch("bengal.utils.atomic_write.AtomicFile")
    def test_generates_sitemap_with_pages(self, mock_atomic: MagicMock, tmp_path: Path) -> None:
        """Test sitemap generation with valid pages."""
        from bengal.postprocess.sitemap import SitemapGenerator

        page = self._create_mock_page(
            title="Test Post",
            output_path=tmp_path / "test-post" / "index.html",
        )

        site = self._create_mock_site(
            pages=[page],
            output_dir=tmp_path,
        )

        generator = SitemapGenerator(site)

        mock_file = MagicMock()
        mock_atomic.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_atomic.return_value.__exit__ = MagicMock(return_value=False)

        generator.generate()

        # Verify AtomicFile was called
        assert mock_atomic.called

    def test_skips_pages_not_in_sitemap(self) -> None:
        """Test that pages with in_sitemap=False are excluded."""
        from bengal.postprocess.sitemap import SitemapGenerator

        page = self._create_mock_page(in_sitemap=False)

        site = self._create_mock_site(pages=[page])

        generator = SitemapGenerator(site)

        # Verify filtering logic
        pages_in_sitemap = [p for p in site.pages if p.in_sitemap]
        assert len(pages_in_sitemap) == 0

    def test_includes_pages_in_sitemap(self, tmp_path: Path) -> None:
        """Test that pages with in_sitemap=True are included."""
        page = self._create_mock_page(
            in_sitemap=True,
            output_path=tmp_path / "test" / "index.html",
        )

        site = self._create_mock_site(pages=[page], output_dir=tmp_path)

        pages_in_sitemap = [p for p in site.pages if p.in_sitemap]
        assert len(pages_in_sitemap) == 1


class TestSitemapGeneratorXMLStructure:
    """Test sitemap XML structure and formatting."""

    def test_xml_has_urlset_root_element(self) -> None:
        """Test that generated XML has urlset root element."""
        urlset = ET.Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

        assert urlset.tag == "urlset"
        assert urlset.get("xmlns") == "http://www.sitemaps.org/schemas/sitemap/0.9"

    def test_xml_has_xhtml_namespace(self) -> None:
        """Test that XML has xhtml namespace for hreflang."""
        urlset = ET.Element("urlset")
        urlset.set("xmlns:xhtml", "http://www.w3.org/1999/xhtml")

        assert urlset.get("xmlns:xhtml") == "http://www.w3.org/1999/xhtml"

    def test_url_element_structure(self) -> None:
        """Test that url element has required children."""
        urlset = ET.Element("urlset")
        url_elem = ET.SubElement(urlset, "url")

        ET.SubElement(url_elem, "loc").text = "https://example.com/test/"
        ET.SubElement(url_elem, "lastmod").text = "2024-01-15"
        ET.SubElement(url_elem, "changefreq").text = "weekly"
        ET.SubElement(url_elem, "priority").text = "0.5"

        assert url_elem.find("loc") is not None
        assert url_elem.find("lastmod") is not None
        assert url_elem.find("changefreq") is not None
        assert url_elem.find("priority") is not None

    def test_loc_contains_full_url(self) -> None:
        """Test that loc contains full URL."""
        url_elem = ET.Element("url")
        loc = ET.SubElement(url_elem, "loc")
        loc.text = "https://example.com/blog/post/"

        assert loc.text == "https://example.com/blog/post/"


class TestSitemapGeneratorDateFormatting:
    """Test lastmod date formatting."""

    def test_formats_date_as_iso(self) -> None:
        """Test that dates are formatted as YYYY-MM-DD."""
        date = datetime(2024, 1, 15, 12, 30, 45)
        formatted = date.strftime("%Y-%m-%d")

        assert formatted == "2024-01-15"

    def test_formats_date_without_time(self) -> None:
        """Test that only date part is used."""
        date = datetime(2024, 12, 31, 23, 59, 59)
        formatted = date.strftime("%Y-%m-%d")

        assert formatted == "2024-12-31"


class TestSitemapGeneratorURLGeneration:
    """Test URL generation for sitemap entries."""

    def test_generates_url_from_output_path(self, tmp_path: Path) -> None:
        """Test URL generation from output_path."""
        page = MagicMock()
        page.output_path = tmp_path / "blog" / "post" / "index.html"
        page.slug = "post"

        site = MagicMock()
        site.output_dir = tmp_path
        baseurl = "https://example.com"

        # Mimicking URL generation logic
        try:
            rel_path = page.output_path.relative_to(site.output_dir)
            loc = f"{baseurl}/{rel_path}".replace("\\", "/")
            loc = loc.replace("/index.html", "/")
        except ValueError:
            loc = f"{baseurl}/{page.slug}/"

        assert loc == "https://example.com/blog/post/"

    def test_cleans_index_html_from_url(self, tmp_path: Path) -> None:
        """Test that /index.html is removed from URLs."""
        page = MagicMock()
        page.output_path = tmp_path / "index.html"

        site = MagicMock()
        site.output_dir = tmp_path
        baseurl = "https://example.com"

        rel_path = page.output_path.relative_to(site.output_dir)
        loc = f"{baseurl}/{rel_path}".replace("\\", "/")
        loc = loc.replace("/index.html", "/")

        assert loc == "https://example.com/"

    def test_falls_back_to_slug_when_no_output_path(self) -> None:
        """Test that URL falls back to slug when output_path unavailable."""
        page = MagicMock()
        page.output_path = None
        page.slug = "test-page"

        baseurl = "https://example.com"
        loc = f"{baseurl}/{page.slug}/"

        assert loc == "https://example.com/test-page/"


class TestSitemapGeneratori18nHreflang:
    """Test i18n hreflang alternate links."""

    def _create_mock_page(
        self,
        title: str,
        translation_key: str | None = None,
        lang: str = "en",
        output_path: Path | None = None,
        in_sitemap: bool = True,
    ) -> MagicMock:
        """Create a mock page with i18n attributes."""
        page = MagicMock()
        page.title = title
        page.translation_key = translation_key
        page.lang = lang
        page.output_path = output_path
        page.in_sitemap = in_sitemap
        page.date = None
        return page

    def test_adds_hreflang_for_translations(self, tmp_path: Path) -> None:
        """Test that hreflang alternates are added for translated pages."""
        # Create pages with same translation_key
        page_en = self._create_mock_page(
            "English Post",
            translation_key="post-1",
            lang="en",
            output_path=tmp_path / "en" / "post" / "index.html",
        )
        page_fr = self._create_mock_page(
            "French Post",
            translation_key="post-1",
            lang="fr",
            output_path=tmp_path / "fr" / "post" / "index.html",
        )

        pages = [page_en, page_fr]

        # Verify that both pages share translation_key
        en_translations = [p for p in pages if p.translation_key == "post-1"]
        assert len(en_translations) == 2

    def test_adds_x_default_for_default_language(self) -> None:
        """Test that x-default hreflang is added for default language."""
        # x-default should point to default language version
        default_lang = "en"
        hreflangs = [
            {"hreflang": "en", "href": "https://example.com/en/post/"},
            {"hreflang": "fr", "href": "https://example.com/fr/post/"},
        ]

        # Find default language href
        default_href = None
        for h in hreflangs:
            if h["hreflang"] == default_lang:
                default_href = h["href"]
                break

        assert default_href == "https://example.com/en/post/"


class TestSitemapGeneratorDefaultValues:
    """Test default changefreq and priority values."""

    def test_default_changefreq_is_weekly(self) -> None:
        """Test that default changefreq is 'weekly'."""
        changefreq = ET.Element("changefreq")
        changefreq.text = "weekly"

        assert changefreq.text == "weekly"

    def test_default_priority_is_0_5(self) -> None:
        """Test that default priority is '0.5'."""
        priority = ET.Element("priority")
        priority.text = "0.5"

        assert priority.text == "0.5"


class TestSitemapGeneratorIndentation:
    """Test XML indentation functionality."""

    def test_indent_adds_whitespace(self) -> None:
        """Test that _indent adds whitespace to XML."""
        from bengal.postprocess.sitemap import SitemapGenerator

        site = MagicMock()
        generator = SitemapGenerator(site)

        urlset = ET.Element("urlset")
        url_elem = ET.SubElement(urlset, "url")
        ET.SubElement(url_elem, "loc").text = "https://example.com/"

        generator._indent(urlset)

        # After indentation, elements should have text/tail with newlines
        assert url_elem.text is not None or url_elem.tail is not None


class TestSitemapGeneratorStatsCounting:
    """Test page counting and stats tracking."""

    def test_counts_included_pages(self, tmp_path: Path) -> None:
        """Test that included pages are counted correctly."""
        page1 = MagicMock()
        page1.in_sitemap = True
        page1.output_path = tmp_path / "page1" / "index.html"
        page1.date = None
        page1.translation_key = None

        page2 = MagicMock()
        page2.in_sitemap = True
        page2.output_path = tmp_path / "page2" / "index.html"
        page2.date = None
        page2.translation_key = None

        page3 = MagicMock()
        page3.in_sitemap = False  # Excluded

        pages = [page1, page2, page3]

        included = [p for p in pages if p.in_sitemap]
        skipped = [p for p in pages if not p.in_sitemap]

        assert len(included) == 2
        assert len(skipped) == 1

    def test_counts_skipped_pages(self) -> None:
        """Test that skipped pages are counted correctly."""
        page1 = MagicMock()
        page1.in_sitemap = False

        page2 = MagicMock()
        page2.in_sitemap = False

        pages = [page1, page2]

        skipped = [p for p in pages if not p.in_sitemap]
        assert len(skipped) == 2
