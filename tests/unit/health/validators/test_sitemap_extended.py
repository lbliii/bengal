"""
Extended tests for sitemap validator.

Additional tests that would have caught the unused coverage calculation bug.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bengal.health.report import CheckStatus
from bengal.health.validators.sitemap import SitemapValidator


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site for testing."""
    site = Mock()
    site.output_dir = tmp_path
    site.config = {"baseurl": "https://example.com"}

    # Create mock pages (5 non-draft, 2 draft)
    pages = []
    for _i in range(5):
        page = Mock()
        page.metadata = {"draft": False}
        pages.append(page)

    for _i in range(2):
        page = Mock()
        page.metadata = {"draft": True}
        pages.append(page)

    site.pages = pages
    return site


class TestSitemapValidatorCoverage:
    """Tests for sitemap coverage calculation."""

    def test_coverage_warning_when_pages_missing(self, mock_site, tmp_path):
        """Warns when sitemap has fewer URLs than publishable pages."""
        # Create sitemap with only 3 URLs (site has 5 non-draft pages)
        sitemap_path = tmp_path / "sitemap.xml"
        sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://example.com/page1/</loc></url>
    <url><loc>https://example.com/page2/</loc></url>
    <url><loc>https://example.com/page3/</loc></url>
</urlset>"""
        sitemap_path.write_text(sitemap_content)

        validator = SitemapValidator()
        results = validator.validate(mock_site)

        # Should warn about coverage
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        coverage_warnings = [r for r in warning_results if "missing" in r.message.lower()]
        assert len(coverage_warnings) >= 1

        # Warning should mention the counts
        warning_msg = coverage_warnings[0].message
        assert "3" in warning_msg  # sitemap count
        assert "5" in warning_msg  # publishable page count

    def test_no_coverage_warning_when_all_pages_included(self, mock_site, tmp_path):
        """No warning when sitemap includes all publishable pages."""
        # Create sitemap with 5 URLs (matches 5 non-draft pages)
        sitemap_path = tmp_path / "sitemap.xml"
        sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://example.com/page1/</loc></url>
    <url><loc>https://example.com/page2/</loc></url>
    <url><loc>https://example.com/page3/</loc></url>
    <url><loc>https://example.com/page4/</loc></url>
    <url><loc>https://example.com/page5/</loc></url>
</urlset>"""
        sitemap_path.write_text(sitemap_content)

        validator = SitemapValidator()
        results = validator.validate(mock_site)

        # Should NOT warn about coverage
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        coverage_warnings = [r for r in warning_results if "missing" in r.message.lower()]
        assert len(coverage_warnings) == 0

    def test_no_warning_when_sitemap_has_more_urls(self, mock_site, tmp_path):
        """
        No warning when sitemap has MORE URLs than pages.

        This is normal - generated pages like tags/archives add URLs.
        """
        # Create sitemap with 7 URLs (more than 5 non-draft pages)
        sitemap_path = tmp_path / "sitemap.xml"
        sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://example.com/page1/</loc></url>
    <url><loc>https://example.com/page2/</loc></url>
    <url><loc>https://example.com/page3/</loc></url>
    <url><loc>https://example.com/page4/</loc></url>
    <url><loc>https://example.com/page5/</loc></url>
    <url><loc>https://example.com/tags/python/</loc></url>
    <url><loc>https://example.com/archives/2024/</loc></url>
</urlset>"""
        sitemap_path.write_text(sitemap_content)

        validator = SitemapValidator()
        results = validator.validate(mock_site)

        # Should NOT warn about extra URLs
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        assert not any("missing" in r.message.lower() for r in warning_results)

    def test_draft_pages_not_counted_for_coverage(self, mock_site, tmp_path):
        """Draft pages are not counted for coverage calculation."""
        # Site has 5 non-draft + 2 draft = 7 total, but only 5 publishable
        # Create sitemap with 5 URLs
        sitemap_path = tmp_path / "sitemap.xml"
        sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://example.com/page1/</loc></url>
    <url><loc>https://example.com/page2/</loc></url>
    <url><loc>https://example.com/page3/</loc></url>
    <url><loc>https://example.com/page4/</loc></url>
    <url><loc>https://example.com/page5/</loc></url>
</urlset>"""
        sitemap_path.write_text(sitemap_content)

        validator = SitemapValidator()
        results = validator.validate(mock_site)

        # Should NOT warn - 5 URLs = 5 publishable pages
        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        coverage_warnings = [r for r in warning_results if "missing" in r.message.lower()]
        assert len(coverage_warnings) == 0


class TestSitemapValidatorEmptyStates:
    """Tests for empty/edge case states."""

    def test_handles_zero_publishable_pages(self, tmp_path):
        """Handles site with no publishable pages."""
        site = Mock()
        site.output_dir = tmp_path
        site.config = {"baseurl": "https://example.com"}

        # All pages are drafts
        page = Mock()
        page.metadata = {"draft": True}
        site.pages = [page]

        sitemap_path = tmp_path / "sitemap.xml"
        sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
</urlset>"""
        sitemap_path.write_text(sitemap_content)

        validator = SitemapValidator()
        results = validator.validate(site)

        # Should not crash on division by zero
        # May warn about no URLs, but should not warn about coverage
        error_results = [r for r in results if r.status == CheckStatus.ERROR]
        # Check there's no crash-related error
        assert not any("division" in str(r.message).lower() for r in error_results)


class TestSitemapValidatorCodes:
    """Tests for health check codes."""

    def test_coverage_warning_has_code_H509(self, mock_site, tmp_path):
        """Coverage warning has code H509."""
        sitemap_path = tmp_path / "sitemap.xml"
        sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://example.com/page1/</loc></url>
</urlset>"""
        sitemap_path.write_text(sitemap_content)

        validator = SitemapValidator()
        results = validator.validate(mock_site)

        warning_results = [r for r in results if r.status == CheckStatus.WARNING]
        coverage_warnings = [r for r in warning_results if "missing" in r.message.lower()]

        if coverage_warnings:
            assert coverage_warnings[0].code == "H509"
