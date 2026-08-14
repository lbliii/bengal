"""
Tests for empty RSS feed and sitemap handling.

Verifies that empty sites don't produce invalid XML.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from pathlib import Path


class TestEmptySitemap:
    """Tests for empty sitemap handling."""

    def test_sitemap_skipped_for_empty_site(self, tmp_path: Path) -> None:
        """Test that sitemap generation is skipped for sites with no pages."""
        from bengal.postprocess.sitemap import SitemapGenerator

        # Create mock site with no pages
        mock_site = MagicMock()
        mock_site.pages = []
        mock_site.output_dir = tmp_path

        generator = SitemapGenerator(mock_site)

        # Replace the logger with a mock to capture calls
        mock_log = MagicMock()
        generator.logger = mock_log

        generator.generate()

        # Should log that generation was skipped
        mock_log.info.assert_called_once()
        call_args = mock_log.info.call_args
        assert call_args[0][0] == "sitemap_skipped"
        assert call_args[1]["reason"] == "no_pages"

        # No sitemap file should be created
        sitemap_path = tmp_path / "sitemap.xml"
        assert not sitemap_path.exists()

    def test_sitemap_generated_with_pages(self, tmp_path: Path) -> None:
        """Test that sitemap is generated when pages exist."""
        from bengal.postprocess.sitemap import SitemapGenerator

        # Create mock site with pages
        mock_page = MagicMock()
        mock_page.output_path = tmp_path / "test" / "index.html"
        mock_page.date = None
        mock_page.translation_key = None

        mock_site = MagicMock()
        mock_site.pages = [mock_page]
        mock_site.output_dir = tmp_path
        mock_site.config = {"baseurl": "https://example.com"}

        # Create output directory structure
        (tmp_path / "test").mkdir(parents=True, exist_ok=True)

        generator = SitemapGenerator(mock_site)
        generator.logger = MagicMock()  # Suppress logger output

        generator.generate()

        # Sitemap should be created
        sitemap_path = tmp_path / "sitemap.xml"
        assert sitemap_path.exists()


class TestEmptyRSS:
    """Tests for empty RSS feed handling."""

    def test_rss_written_for_site_without_dates(self, tmp_path: Path) -> None:
        """Sites without dated pages still get a valid empty rss.xml."""
        from bengal.postprocess.rss import RSSGenerator

        mock_page = MagicMock()
        mock_page.date = None

        mock_site = MagicMock()
        mock_site.pages = [mock_page]
        mock_site.output_dir = tmp_path
        mock_site.title = "Test Site"
        mock_site.baseurl = "https://example.com"
        mock_site.description = "Test"
        mock_site.config = {"i18n": {}}

        generator = RSSGenerator(mock_site)
        mock_log = MagicMock()
        generator.logger = mock_log

        generator.generate()

        assert any(
            call.args and call.args[0] == "rss_empty_feed" for call in mock_log.info.call_args_list
        )

        rss_path = tmp_path / "rss.xml"
        assert rss_path.exists()
        rss_content = rss_path.read_text()
        assert "<rss" in rss_content
        assert "<channel>" in rss_content
        assert "<item>" not in rss_content

    def test_rss_written_for_empty_site(self, tmp_path: Path) -> None:
        """Empty sites still get a valid empty rss.xml when RSS is enabled."""
        from bengal.postprocess.rss import RSSGenerator

        mock_site = MagicMock()
        mock_site.pages = []
        mock_site.output_dir = tmp_path
        mock_site.title = "Test Site"
        mock_site.baseurl = "https://example.com"
        mock_site.description = "Test"
        mock_site.config = {"i18n": {}}

        generator = RSSGenerator(mock_site)
        mock_log = MagicMock()
        generator.logger = mock_log

        generator.generate()

        assert any(
            call.args and call.args[0] == "rss_empty_feed" for call in mock_log.info.call_args_list
        )

        rss_path = tmp_path / "rss.xml"
        assert rss_path.exists()
        assert "<channel>" in rss_path.read_text()

    def test_rss_generated_with_dated_pages(self, tmp_path: Path) -> None:
        """Test that RSS is generated when dated pages exist."""
        from datetime import datetime

        from bengal.postprocess.rss import RSSGenerator

        # Create mock site with dated page
        mock_page = MagicMock()
        mock_page.date = datetime(2025, 1, 1)
        mock_page.title = "Test Post"
        mock_page.output_path = tmp_path / "test" / "index.html"
        mock_page.slug = "test"
        mock_page.content = "Test content"
        mock_page.metadata = {}
        mock_page.lang = "en"

        mock_site = MagicMock()
        mock_site.pages = [mock_page]
        mock_site.output_dir = tmp_path
        mock_site.config = {
            "title": "Test Site",
            "baseurl": "https://example.com",
            "description": "Test",
            "i18n": {},
        }
        # Set properties as string attributes (not Mock objects)
        mock_site.title = "Test Site"
        mock_site.baseurl = "https://example.com"
        mock_site.description = "Test"

        # Create output directory
        (tmp_path / "test").mkdir(parents=True, exist_ok=True)

        generator = RSSGenerator(mock_site)
        generator.logger = MagicMock()  # Suppress logger output

        generator.generate()

        # RSS should be created
        rss_path = tmp_path / "rss.xml"
        assert rss_path.exists()

        # Verify it contains the page
        content = rss_path.read_text()
        assert "Test Post" in content
