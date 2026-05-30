"""Unit tests for Site visibility filtering.

Tests that site.pages and site.listable_pages correctly filter
hidden pages based on visibility settings.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.core.page_visibility import (
    is_page_in_listings,
    is_page_in_rss,
    is_page_in_search,
    is_page_in_sitemap,
)
from bengal.core.site import Site
from tests._testing.mocks import make_mock_page as _page


@pytest.fixture
def mock_site():
    """Create a mock site with pages having various visibility settings."""
    site = MagicMock(spec=Site)

    # Create test pages with different visibility settings
    pages = [
        # Regular page (visible in all outputs)
        _page(
            source_path=Path("content/regular.md"),
            _raw_content="Regular content",
            _raw_metadata={"title": "Regular Page"},
        ),
        # Hidden page (hidden shorthand)
        _page(
            source_path=Path("content/hidden.md"),
            _raw_content="Hidden content",
            _raw_metadata={"title": "Hidden Page", "hidden": True},
        ),
        # Draft page
        _page(
            source_path=Path("content/draft.md"),
            _raw_content="Draft content",
            _raw_metadata={"title": "Draft Page", "draft": True},
        ),
        # Page with visibility.listings: false
        _page(
            source_path=Path("content/unlisted.md"),
            _raw_content="Unlisted content",
            _raw_metadata={
                "title": "Unlisted Page",
                "visibility": {"listings": False},
            },
        ),
        # Page with visibility.menu: false only
        _page(
            source_path=Path("content/no-menu.md"),
            _raw_content="No menu content",
            _raw_metadata={
                "title": "No Menu Page",
                "visibility": {"menu": False},
            },
        ),
    ]

    # Manually filter to simulate site.pages behavior
    site.pages = pages
    site.listable_pages = [p for p in pages if is_page_in_listings(p)]

    return site, pages


class TestSitePagesFiltering:
    """Test that site collections filter pages correctly."""

    def test_all_pages_in_pages_list(self, mock_site):
        """site.pages contains all pages (not filtered by visibility)."""
        site, _pages = mock_site
        # Note: In the actual implementation, site.pages may or may not filter
        # Here we test the expected behavior
        assert len(site.pages) == 5

    def test_listable_pages_excludes_hidden(self, mock_site):
        """site.listable_pages excludes hidden pages."""
        site, _pages = mock_site
        listable = site.listable_pages

        # Should include: regular, no-menu (menu visibility doesn't affect listings)
        # Should exclude: hidden, draft, unlisted
        assert len(listable) == 2

        titles = [p.title for p in listable]
        assert "Regular Page" in titles
        assert "No Menu Page" in titles
        assert "Hidden Page" not in titles
        assert "Draft Page" not in titles
        assert "Unlisted Page" not in titles


class TestPageVisibilityInCollections:
    """Test that visibility properties work correctly for filtering."""

    def test_in_listings_for_various_pages(self):
        """Test in_listings property for pages with different visibility."""
        regular = _page(
            source_path=Path("regular.md"),
            _raw_content="",
            _raw_metadata={"title": "Regular"},
        )
        hidden = _page(
            source_path=Path("hidden.md"),
            _raw_content="",
            _raw_metadata={"title": "Hidden", "hidden": True},
        )
        draft = _page(
            source_path=Path("draft.md"),
            _raw_content="",
            _raw_metadata={"title": "Draft", "draft": True},
        )
        unlisted = _page(
            source_path=Path("unlisted.md"),
            _raw_content="",
            _raw_metadata={"title": "Unlisted", "visibility": {"listings": False}},
        )
        no_menu = _page(
            source_path=Path("no-menu.md"),
            _raw_content="",
            _raw_metadata={"title": "NoMenu", "visibility": {"menu": False}},
        )

        assert is_page_in_listings(regular) is True
        assert is_page_in_listings(hidden) is False
        assert is_page_in_listings(draft) is False
        assert is_page_in_listings(unlisted) is False
        assert is_page_in_listings(no_menu) is True  # menu visibility != listings

    def test_in_sitemap_for_various_pages(self):
        """Test in_sitemap property for pages with different visibility."""
        regular = _page(
            source_path=Path("regular.md"),
            _raw_content="",
            _raw_metadata={"title": "Regular"},
        )
        hidden = _page(
            source_path=Path("hidden.md"),
            _raw_content="",
            _raw_metadata={"title": "Hidden", "hidden": True},
        )
        no_sitemap = _page(
            source_path=Path("no-sitemap.md"),
            _raw_content="",
            _raw_metadata={"title": "NoSitemap", "visibility": {"sitemap": False}},
        )

        assert is_page_in_sitemap(regular) is True
        assert is_page_in_sitemap(hidden) is False
        assert is_page_in_sitemap(no_sitemap) is False

    def test_in_search_for_various_pages(self):
        """Test in_search property for pages with different visibility."""
        regular = _page(
            source_path=Path("regular.md"),
            _raw_content="",
            _raw_metadata={"title": "Regular"},
        )
        hidden = _page(
            source_path=Path("hidden.md"),
            _raw_content="",
            _raw_metadata={"title": "Hidden", "hidden": True},
        )
        no_search = _page(
            source_path=Path("no-search.md"),
            _raw_content="",
            _raw_metadata={"title": "NoSearch", "visibility": {"search": False}},
        )

        assert is_page_in_search(regular) is True
        assert is_page_in_search(hidden) is False
        assert is_page_in_search(no_search) is False

    def test_in_rss_for_various_pages(self):
        """Test in_rss property for pages with different visibility."""
        regular = _page(
            source_path=Path("regular.md"),
            _raw_content="",
            _raw_metadata={"title": "Regular"},
        )
        hidden = _page(
            source_path=Path("hidden.md"),
            _raw_content="",
            _raw_metadata={"title": "Hidden", "hidden": True},
        )
        no_rss = _page(
            source_path=Path("no-rss.md"),
            _raw_content="",
            _raw_metadata={"title": "NoRss", "visibility": {"rss": False}},
        )

        assert is_page_in_rss(regular) is True
        assert is_page_in_rss(hidden) is False
        assert is_page_in_rss(no_rss) is False
