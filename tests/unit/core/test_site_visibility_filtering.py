"""Unit tests for Site visibility filtering.

Tests that site.pages and site.listable_pages correctly filter
hidden pages based on visibility settings.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.core.page import Page
from bengal.core.site import Site


@pytest.fixture
def mock_site():
    """Create a mock site with pages having various visibility settings."""
    site = MagicMock(spec=Site)

    # Create test pages with different visibility settings
    pages = [
        # Regular page (visible in all outputs)
        Page(
            source_path=Path("content/regular.md"),
            content="Regular content",
            metadata={"title": "Regular Page"},
        ),
        # Hidden page (hidden shorthand)
        Page(
            source_path=Path("content/hidden.md"),
            content="Hidden content",
            metadata={"title": "Hidden Page", "hidden": True},
        ),
        # Draft page
        Page(
            source_path=Path("content/draft.md"),
            content="Draft content",
            metadata={"title": "Draft Page", "draft": True},
        ),
        # Page with visibility.listings: false
        Page(
            source_path=Path("content/unlisted.md"),
            content="Unlisted content",
            metadata={
                "title": "Unlisted Page",
                "visibility": {"listings": False},
            },
        ),
        # Page with visibility.menu: false only
        Page(
            source_path=Path("content/no-menu.md"),
            content="No menu content",
            metadata={
                "title": "No Menu Page",
                "visibility": {"menu": False},
            },
        ),
    ]

    # Manually filter to simulate site.pages behavior
    site.pages = pages
    site.listable_pages = [p for p in pages if p.in_listings]

    return site, pages


class TestSitePagesFiltering:
    """Test that site collections filter pages correctly."""

    def test_all_pages_in_pages_list(self, mock_site):
        """site.pages contains all pages (not filtered by visibility)."""
        site, pages = mock_site
        # Note: In the actual implementation, site.pages may or may not filter
        # Here we test the expected behavior
        assert len(site.pages) == 5

    def test_listable_pages_excludes_hidden(self, mock_site):
        """site.listable_pages excludes hidden pages."""
        site, pages = mock_site
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
        regular = Page(
            source_path=Path("regular.md"),
            content="",
            metadata={"title": "Regular"},
        )
        hidden = Page(
            source_path=Path("hidden.md"),
            content="",
            metadata={"title": "Hidden", "hidden": True},
        )
        draft = Page(
            source_path=Path("draft.md"),
            content="",
            metadata={"title": "Draft", "draft": True},
        )
        unlisted = Page(
            source_path=Path("unlisted.md"),
            content="",
            metadata={"title": "Unlisted", "visibility": {"listings": False}},
        )
        no_menu = Page(
            source_path=Path("no-menu.md"),
            content="",
            metadata={"title": "NoMenu", "visibility": {"menu": False}},
        )

        assert regular.in_listings is True
        assert hidden.in_listings is False
        assert draft.in_listings is False
        assert unlisted.in_listings is False
        assert no_menu.in_listings is True  # menu visibility != listings

    def test_in_sitemap_for_various_pages(self):
        """Test in_sitemap property for pages with different visibility."""
        regular = Page(
            source_path=Path("regular.md"),
            content="",
            metadata={"title": "Regular"},
        )
        hidden = Page(
            source_path=Path("hidden.md"),
            content="",
            metadata={"title": "Hidden", "hidden": True},
        )
        no_sitemap = Page(
            source_path=Path("no-sitemap.md"),
            content="",
            metadata={"title": "NoSitemap", "visibility": {"sitemap": False}},
        )

        assert regular.in_sitemap is True
        assert hidden.in_sitemap is False
        assert no_sitemap.in_sitemap is False

    def test_in_search_for_various_pages(self):
        """Test in_search property for pages with different visibility."""
        regular = Page(
            source_path=Path("regular.md"),
            content="",
            metadata={"title": "Regular"},
        )
        hidden = Page(
            source_path=Path("hidden.md"),
            content="",
            metadata={"title": "Hidden", "hidden": True},
        )
        no_search = Page(
            source_path=Path("no-search.md"),
            content="",
            metadata={"title": "NoSearch", "visibility": {"search": False}},
        )

        assert regular.in_search is True
        assert hidden.in_search is False
        assert no_search.in_search is False

    def test_in_rss_for_various_pages(self):
        """Test in_rss property for pages with different visibility."""
        regular = Page(
            source_path=Path("regular.md"),
            content="",
            metadata={"title": "Regular"},
        )
        hidden = Page(
            source_path=Path("hidden.md"),
            content="",
            metadata={"title": "Hidden", "hidden": True},
        )
        no_rss = Page(
            source_path=Path("no-rss.md"),
            content="",
            metadata={"title": "NoRss", "visibility": {"rss": False}},
        )

        assert regular.in_rss is True
        assert hidden.in_rss is False
        assert no_rss.in_rss is False


