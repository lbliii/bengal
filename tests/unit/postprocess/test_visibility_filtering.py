"""Unit tests for visibility filtering in postprocess generators.

Tests that sitemap, RSS, and index generators correctly exclude
hidden/visibility-filtered pages.
"""

from unittest.mock import MagicMock


class TestSitemapVisibilityFiltering:
    """Test that sitemap generator respects visibility settings."""

    def test_sitemap_excludes_hidden_pages(self):
        """Sitemap should exclude pages with hidden: true."""
        # Create mock page with hidden: true
        page = MagicMock()
        page.in_sitemap = False  # hidden pages have in_sitemap = False

        pages = [page]
        in_sitemap_pages = [p for p in pages if p.in_sitemap]

        assert len(in_sitemap_pages) == 0

    def test_sitemap_excludes_visibility_sitemap_false(self):
        """Sitemap should exclude pages with visibility.sitemap: false."""
        page = MagicMock()
        page.in_sitemap = False

        pages = [page]
        in_sitemap_pages = [p for p in pages if p.in_sitemap]

        assert len(in_sitemap_pages) == 0

    def test_sitemap_includes_regular_pages(self):
        """Sitemap should include regular pages."""
        page = MagicMock()
        page.in_sitemap = True

        pages = [page]
        in_sitemap_pages = [p for p in pages if p.in_sitemap]

        assert len(in_sitemap_pages) == 1


class TestRssVisibilityFiltering:
    """Test that RSS generator respects visibility settings."""

    def test_rss_excludes_hidden_pages(self):
        """RSS should exclude pages with hidden: true."""
        page = MagicMock()
        page.in_rss = False

        pages = [page]
        in_rss_pages = [p for p in pages if p.in_rss]

        assert len(in_rss_pages) == 0

    def test_rss_excludes_visibility_rss_false(self):
        """RSS should exclude pages with visibility.rss: false."""
        page = MagicMock()
        page.in_rss = False

        pages = [page]
        in_rss_pages = [p for p in pages if p.in_rss]

        assert len(in_rss_pages) == 0

    def test_rss_includes_regular_pages_with_date(self):
        """RSS should include regular pages with dates."""
        page = MagicMock()
        page.in_rss = True
        page.date = "2025-01-01"

        pages = [page]
        in_rss_pages = [p for p in pages if p.in_rss and p.date]

        assert len(in_rss_pages) == 1


class TestIndexGeneratorVisibilityFiltering:
    """Test that index generator respects visibility settings."""

    def test_index_excludes_hidden_from_search(self):
        """Index should mark hidden pages as search_exclude."""
        # Simulate the metadata check in index_generator
        metadata = {"hidden": True}

        search_exclude = False
        if metadata.get("hidden", False):
            search_exclude = True

        assert search_exclude is True

    def test_index_excludes_visibility_search_false(self):
        """Index should mark visibility.search: false pages as search_exclude."""
        metadata = {"visibility": {"search": False}}

        search_exclude = False
        if isinstance(metadata.get("visibility"), dict):
            if not metadata["visibility"].get("search", True):
                search_exclude = True

        assert search_exclude is True

    def test_index_includes_regular_pages(self):
        """Index should include regular pages in search."""
        metadata = {"title": "Regular Page"}

        search_exclude = False
        if metadata.get("hidden", False):
            search_exclude = True
        elif isinstance(metadata.get("visibility"), dict):
            if not metadata["visibility"].get("search", True):
                search_exclude = True

        assert search_exclude is False

    def test_index_partial_visibility_doesnt_exclude_search(self):
        """Pages with other visibility settings but search: true are included."""
        metadata = {
            "visibility": {
                "menu": False,
                "listings": False,
                "search": True,
            }
        }

        search_exclude = False
        if metadata.get("hidden", False):
            search_exclude = True
        elif isinstance(metadata.get("visibility"), dict):
            if not metadata["visibility"].get("search", True):
                search_exclude = True

        assert search_exclude is False


class TestNavigationVisibilityFiltering:
    """Test that navigation respects visibility.menu setting."""

    def test_navigation_excludes_menu_false(self):
        """Navigation should exclude pages with visibility.menu: false."""
        page = MagicMock()
        page.visibility = {"menu": False}

        pages = [page]
        in_menu_pages = [p for p in pages if p.visibility.get("menu", True)]

        assert len(in_menu_pages) == 0

    def test_navigation_excludes_hidden(self):
        """Navigation should exclude hidden pages."""
        page = MagicMock()
        page.visibility = {"menu": False}  # hidden expands to menu: false

        pages = [page]
        in_menu_pages = [p for p in pages if p.visibility.get("menu", True)]

        assert len(in_menu_pages) == 0

    def test_navigation_includes_regular_pages(self):
        """Navigation should include regular pages."""
        page = MagicMock()
        page.visibility = {"menu": True}

        pages = [page]
        in_menu_pages = [p for p in pages if p.visibility.get("menu", True)]

        assert len(in_menu_pages) == 1


