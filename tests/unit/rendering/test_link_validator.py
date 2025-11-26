"""
Tests for link validation in link_validator.py.

Tests internal link validation, including:
- Relative path resolution
- Fragment-only links
- Missing page detection
- Trailing slash normalization
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.rendering.link_validator import LinkValidator


@pytest.fixture
def mock_site():
    """Create a mock site with sample pages."""
    site = MagicMock()

    # Create mock pages with URLs
    page1 = MagicMock()
    page1.url = "/docs/"
    page1.permalink = None
    page1.source_path = Path("content/docs/_index.md")
    page1.links = []

    page2 = MagicMock()
    page2.url = "/docs/getting-started/"
    page2.permalink = None
    page2.source_path = Path("content/docs/getting-started.md")
    page2.links = []

    page3 = MagicMock()
    page3.url = "/blog/"
    page3.permalink = None
    page3.source_path = Path("content/blog/_index.md")
    page3.links = []

    page4 = MagicMock()
    page4.url = "/about/"
    page4.permalink = "/about/"
    page4.source_path = Path("content/about.md")
    page4.links = []

    site.pages = [page1, page2, page3, page4]
    return site


@pytest.fixture
def validator(mock_site):
    """Create a validator with the mock site."""
    return LinkValidator(site=mock_site)


class TestLinkValidatorInitialization:
    """Test validator initialization."""

    def test_init_without_site(self):
        """Test initialization without a site."""
        validator = LinkValidator()
        assert validator._site is None
        assert validator._page_urls is None

    def test_init_with_site(self, mock_site):
        """Test initialization with a site."""
        validator = LinkValidator(site=mock_site)
        assert validator._site == mock_site


class TestExternalLinkSkipping:
    """Test that external links are skipped."""

    def test_http_links_are_valid(self, validator):
        """Test that HTTP links are always valid (skipped)."""
        page = MagicMock()
        page.url = "/docs/"

        assert validator._is_valid_link("http://example.com", page) is True
        assert "http://example.com" in validator.validated_urls

    def test_https_links_are_valid(self, validator):
        """Test that HTTPS links are always valid (skipped)."""
        page = MagicMock()
        page.url = "/docs/"

        assert validator._is_valid_link("https://example.com/path", page) is True

    def test_mailto_links_are_valid(self, validator):
        """Test that mailto links are always valid (skipped)."""
        page = MagicMock()
        page.url = "/docs/"

        assert validator._is_valid_link("mailto:user@example.com", page) is True

    def test_tel_links_are_valid(self, validator):
        """Test that tel links are always valid (skipped)."""
        page = MagicMock()
        page.url = "/docs/"

        assert validator._is_valid_link("tel:+1234567890", page) is True

    def test_data_urls_are_valid(self, validator):
        """Test that data URLs are always valid (skipped)."""
        page = MagicMock()
        page.url = "/docs/"

        assert validator._is_valid_link("data:image/png;base64,abc", page) is True


class TestFragmentLinks:
    """Test fragment-only links."""

    def test_fragment_only_links_are_valid(self, validator):
        """Test that fragment-only links are always valid."""
        page = MagicMock()
        page.url = "/docs/"

        assert validator._is_valid_link("#section-name", page) is True
        assert validator._is_valid_link("#", page) is True


class TestInternalLinkValidation:
    """Test internal link validation against page URLs."""

    def test_valid_absolute_link(self, validator, mock_site):
        """Test that absolute links to existing pages are valid."""
        page = MagicMock()
        page.url = "/docs/"

        # Initialize the page URL index
        validator._page_urls = validator._build_page_url_index(mock_site)

        assert validator._is_valid_link("/docs/getting-started/", page) is True

    def test_valid_relative_link(self, validator, mock_site):
        """Test that relative links to existing pages are valid."""
        page = MagicMock()
        page.url = "/docs/"

        validator._page_urls = validator._build_page_url_index(mock_site)

        assert validator._is_valid_link("getting-started/", page) is True

    def test_invalid_link_to_missing_page(self, validator, mock_site):
        """Test that links to missing pages are invalid."""
        page = MagicMock()
        page.url = "/docs/"

        validator._page_urls = validator._build_page_url_index(mock_site)

        assert validator._is_valid_link("/nonexistent/", page) is False

    def test_trailing_slash_normalization(self, validator, mock_site):
        """Test that links work with or without trailing slashes."""
        page = MagicMock()
        page.url = "/docs/"

        validator._page_urls = validator._build_page_url_index(mock_site)

        # Both should work
        assert validator._is_valid_link("/docs/getting-started", page) is True
        assert validator._is_valid_link("/docs/getting-started/", page) is True

    def test_link_with_fragment(self, validator, mock_site):
        """Test that links with fragments resolve to the base page."""
        page = MagicMock()
        page.url = "/docs/"

        validator._page_urls = validator._build_page_url_index(mock_site)

        # Link with fragment should validate against base URL
        assert validator._is_valid_link("/docs/getting-started/#section", page) is True
        assert validator._is_valid_link("/nonexistent/#section", page) is False


class TestPageUrlIndex:
    """Test the page URL index building."""

    def test_build_page_url_index(self, mock_site):
        """Test that the page URL index includes all URL variants."""
        validator = LinkValidator()
        index = validator._build_page_url_index(mock_site)

        # Should include URLs with and without trailing slashes
        assert "/docs/" in index
        assert "/docs" in index
        assert "/docs/getting-started/" in index
        assert "/docs/getting-started" in index

    def test_index_includes_permalinks(self):
        """Test that the index includes permalinks."""
        site = MagicMock()
        page = MagicMock()
        page.url = "/blog/post/"
        page.permalink = "/custom-url/"
        site.pages = [page]

        validator = LinkValidator()
        index = validator._build_page_url_index(site)

        assert "/blog/post/" in index
        assert "/custom-url/" in index


class TestValidateSite:
    """Test full site validation."""

    def test_validate_site_finds_broken_links(self, mock_site):
        """Test that validate_site finds broken links."""
        # Add broken links to a page
        mock_site.pages[0].links = ["/nonexistent/", "/also-missing/"]

        validator = LinkValidator()
        broken = validator.validate_site(mock_site)

        assert len(broken) == 2
        assert any("/nonexistent/" in str(link) for _, link in broken)

    def test_validate_site_returns_empty_for_valid_links(self, mock_site):
        """Test that validate_site returns empty for valid links."""
        # Add valid links
        mock_site.pages[0].links = ["/docs/getting-started/", "/blog/"]

        validator = LinkValidator()
        broken = validator.validate_site(mock_site)

        assert len(broken) == 0

    def test_validate_site_mixed_links(self, mock_site):
        """Test validation with mix of valid and invalid links."""
        mock_site.pages[0].links = [
            "/docs/getting-started/",  # Valid
            "/missing/",  # Invalid
            "https://external.com",  # Skipped (external)
        ]

        validator = LinkValidator()
        broken = validator.validate_site(mock_site)

        assert len(broken) == 1
        assert broken[0][1] == "/missing/"


class TestGracefulDegradation:
    """Test graceful degradation when data is missing."""

    def test_no_page_url_index_passes_all(self):
        """Test that without URL index, all links pass."""
        validator = LinkValidator()  # No site
        page = MagicMock()
        page.url = "/docs/"

        # Should pass because no index to validate against
        assert validator._is_valid_link("/anything/", page) is True

    def test_page_without_url_passes(self, mock_site):
        """Test that pages without URLs don't cause errors."""
        validator = LinkValidator(site=mock_site)
        page = MagicMock()
        page.url = None  # No URL

        # Should pass because can't resolve
        assert validator._is_valid_link("/anything/", page) is True

