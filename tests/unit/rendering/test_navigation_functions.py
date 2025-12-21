"""
Tests for navigation template functions.

Tests the data provider functions that handle complex logic for
breadcrumbs, pagination, TOC grouping, and navigation trees.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bengal.rendering.template_functions.navigation import (
    get_nav_context,
    get_nav_tree,
    get_pagination_items,
    get_toc_grouped,
)


class TestGetTocGrouped:
    """Test the get_toc_grouped() function for TOC grouping."""

    def test_empty_toc_returns_empty_list(self):
        """Empty TOC items return empty list."""
        result = get_toc_grouped([])
        assert result == []

    def test_single_item_no_grouping(self):
        """Single item at grouping level creates one group."""
        toc_items = [{"id": "section-1", "title": "Section 1", "level": 1}]

        result = get_toc_grouped(toc_items)

        assert len(result) == 1
        assert result[0]["header"] == toc_items[0]
        assert result[0]["children"] == []
        assert not result[0]["is_group"]

    def test_group_with_children(self):
        """Item with children creates a group."""
        toc_items = [
            {"id": "section-1", "title": "Section 1", "level": 1},
            {"id": "section-1-1", "title": "Subsection 1.1", "level": 2},
            {"id": "section-1-2", "title": "Subsection 1.2", "level": 2},
        ]

        result = get_toc_grouped(toc_items)

        assert len(result) == 1
        assert result[0]["header"] == toc_items[0]
        assert len(result[0]["children"]) == 2
        assert result[0]["children"][0] == toc_items[1]
        assert result[0]["children"][1] == toc_items[2]
        assert result[0]["is_group"]

    def test_multiple_groups(self):
        """Multiple H2 sections create multiple groups."""
        toc_items = [
            {"id": "section-1", "title": "Section 1", "level": 1},
            {"id": "section-1-1", "title": "Subsection 1.1", "level": 2},
            {"id": "section-2", "title": "Section 2", "level": 1},
            {"id": "section-2-1", "title": "Subsection 2.1", "level": 2},
        ]

        result = get_toc_grouped(toc_items)

        assert len(result) == 2
        # First group
        assert result[0]["header"]["title"] == "Section 1"
        assert len(result[0]["children"]) == 1
        assert result[0]["is_group"]
        # Second group
        assert result[1]["header"]["title"] == "Section 2"
        assert len(result[1]["children"]) == 1
        assert result[1]["is_group"]

    def test_standalone_item_higher_level(self):
        """H1 items when grouping by H2 are standalone."""
        toc_items = [
            {"id": "title", "title": "Page Title", "level": 0},
            {"id": "section-1", "title": "Section 1", "level": 1},
            {"id": "section-1-1", "title": "Subsection 1.1", "level": 2},
        ]

        result = get_toc_grouped(toc_items)

        assert len(result) == 2
        # H1 is standalone
        assert result[0]["header"]["level"] == 0
        assert not result[0]["is_group"]
        # H2 with children
        assert result[1]["header"]["level"] == 1
        assert result[1]["is_group"]

    def test_deep_nesting(self):
        """Deep nesting (H3, H4, etc.) all become children."""
        toc_items = [
            {"id": "section-1", "title": "Section 1", "level": 1},
            {"id": "section-1-1", "title": "Subsection 1.1", "level": 2},
            {"id": "section-1-1-1", "title": "Subsubsection 1.1.1", "level": 3},
            {"id": "section-1-1-2", "title": "Subsubsection 1.1.2", "level": 3},
            {"id": "section-1-2", "title": "Subsection 1.2", "level": 2},
        ]

        result = get_toc_grouped(toc_items)

        assert len(result) == 1
        assert len(result[0]["children"]) == 4  # All H3+ items are children
        assert result[0]["children"][0]["level"] == 2
        assert result[0]["children"][1]["level"] == 3
        assert result[0]["children"][2]["level"] == 3
        assert result[0]["children"][3]["level"] == 2

    def test_custom_grouping_level(self):
        """Can group by custom level (e.g., H3 instead of H2)."""
        toc_items = [
            {"id": "section-1", "title": "Section 1", "level": 1},
            {"id": "section-1-1", "title": "Subsection 1.1", "level": 2},
            {"id": "section-1-1-1", "title": "Subsubsection 1.1.1", "level": 3},
        ]

        result = get_toc_grouped(toc_items, group_by_level=2)

        assert len(result) == 2  # H1 standalone, H2 with H3 child
        assert result[0]["header"]["level"] == 1
        assert not result[0]["is_group"]
        assert result[1]["header"]["level"] == 2
        assert result[1]["is_group"]
        assert len(result[1]["children"]) == 1


class TestGetPaginationItems:
    """Test the get_pagination_items() function."""

    def test_single_page(self):
        """Single page returns minimal structure."""
        result = get_pagination_items(1, 1, "/blog/")

        assert len(result["pages"]) == 1
        assert result["pages"][0]["num"] == 1
        assert result["pages"][0]["is_current"]
        assert result["prev"] is None
        assert result["next"] is None

    def test_first_page_of_many(self):
        """First page has next but no prev."""
        result = get_pagination_items(1, 10, "/blog/")

        assert result["prev"] is None
        assert result["next"] is not None
        assert result["next"]["num"] == 2
        assert result["next"]["url"] == "/blog/page/2/"
        assert result["pages"][0]["is_current"]

    def test_last_page_of_many(self):
        """Last page has prev but no next."""
        result = get_pagination_items(10, 10, "/blog/")

        assert result["prev"] is not None
        assert result["prev"]["num"] == 9
        assert result["next"] is None
        assert result["pages"][-1]["is_current"]

    def test_middle_page(self):
        """Middle page has both prev and next."""
        result = get_pagination_items(5, 10, "/blog/")

        assert result["prev"]["num"] == 4
        assert result["next"]["num"] == 6

    def test_first_page_url_special_case(self):
        """Page 1 uses base URL, not /page/1/."""
        result = get_pagination_items(1, 10, "/blog/")

        assert result["pages"][0]["url"] == "/blog/"
        # Page 2 should use /page/2/
        assert result["pages"][1]["url"] == "/blog/page/2/"

    def test_ellipsis_markers(self):
        """Ellipsis markers are included when needed."""
        result = get_pagination_items(10, 20, "/blog/", window=2)

        # Should have structure like: 1 ... 8 9 10 11 12 ... 20
        ellipsis_items = [item for item in result["pages"] if item["is_ellipsis"]]
        assert len(ellipsis_items) == 2

        # Ellipsis items have no num or url
        for item in ellipsis_items:
            assert item["num"] is None
            assert item["url"] is None
            assert item["is_ellipsis"]

    def test_window_size(self):
        """Window parameter controls number of pages around current."""
        result = get_pagination_items(10, 20, "/blog/", window=1)

        # With window=1, should show: 1 ... 9 10 11 ... 20
        page_nums = [item["num"] for item in result["pages"] if not item["is_ellipsis"]]
        assert page_nums == [1, 9, 10, 11, 20]

    def test_small_total_no_ellipsis(self):
        """Small total pages show all pages without ellipsis."""
        result = get_pagination_items(3, 5, "/blog/", window=2)

        # Should show all pages: 1 2 3 4 5
        page_nums = [item["num"] for item in result["pages"]]
        assert page_nums == [1, 2, 3, 4, 5]

        ellipsis_items = [item for item in result["pages"] if item["is_ellipsis"]]
        assert len(ellipsis_items) == 0

    def test_base_url_normalized(self):
        """Base URL is normalized (trailing slash handled)."""
        result1 = get_pagination_items(2, 3, "/blog/")
        result2 = get_pagination_items(2, 3, "/blog")

        # Both should generate same URLs
        assert result1["pages"][1]["url"] == result2["pages"][1]["url"]

    def test_current_page_clamped(self):
        """Current page is clamped to valid range."""
        result = get_pagination_items(100, 10, "/blog/")

        # Should clamp to page 10
        assert result["pages"][-1]["is_current"]
        assert result["next"] is None

    def test_first_and_last_links(self):
        """First and last links are always provided."""
        result = get_pagination_items(5, 10, "/blog/")

        assert result["first"]["num"] == 1
        assert result["first"]["url"] == "/blog/"
        assert result["last"]["num"] == 10
        assert result["last"]["url"] == "/blog/page/10/"


class TestGetNavTree:
    """Test the get_nav_tree() function."""

    def test_no_section_returns_empty(self):
        """Page without section returns empty list."""
        page = Mock(spec=["title", "url"])

        result = get_nav_tree(page)

        assert result == []

    def test_no_site_returns_empty(self):
        """Page without site reference returns empty list."""
        # Create page without _site attribute
        current_page = Mock(spec=[])
        current_page._site = None

        result = get_nav_tree(current_page)

        assert result == []

    def test_nav_tree_with_empty_site(self):
        """get_nav_tree with site having no sections returns empty."""
        from bengal.core.nav_tree import NavTreeCache

        # Create mock site with empty sections
        site = Mock()
        site.versioning_enabled = False
        site.sections = []
        site.title = "Test Site"
        site.versions = []

        # Create mock page
        current_page = Mock()
        current_page.url = "/docs/page1/"
        current_page.relative_url = "/docs/page1/"
        current_page.version = None
        current_page._section = None
        current_page._site = site

        # Clear the cache
        NavTreeCache.invalidate()

        result = get_nav_tree(current_page)

        # With no sections, should return empty children list
        assert result == []

    def test_mark_active_trail_false_skips_trail_computation(self):
        """When mark_active_trail=False, trail is not computed."""
        from bengal.core.nav_tree import NavTreeCache

        # Create mock site with empty sections
        site = Mock()
        site.versioning_enabled = False
        site.sections = []
        site.title = "Test Site"
        site.versions = []

        # Create mock page
        current_page = Mock()
        current_page.url = "/docs/page1/"
        current_page.relative_url = "/docs/page1/"
        current_page.version = None
        current_page._section = None
        current_page._site = site

        # Clear the cache
        NavTreeCache.invalidate()

        result = get_nav_tree(current_page, mark_active_trail=False)

        assert result == []


class TestGetNavContext:
    """Test the get_nav_context() function for scoped navigation."""

    def test_no_site_raises_error(self):
        """Page without site reference raises BengalRenderingError."""
        from bengal.errors import BengalRenderingError

        current_page = Mock(spec=[])
        current_page._site = None

        with pytest.raises(BengalRenderingError, match="no site reference"):
            get_nav_context(current_page)

    def test_returns_nav_tree_context(self):
        """Returns NavTreeContext with root node."""
        from bengal.core.nav_tree import NavTreeCache, NavTreeContext

        # Create mock site with empty sections
        site = Mock()
        site.versioning_enabled = False
        site.sections = []
        site.title = "Test Site"
        site.versions = []

        # Create mock page
        current_page = Mock()
        current_page.url = "/docs/page1/"
        current_page.relative_url = "/docs/page1/"
        current_page.version = None
        current_page._section = None
        current_page._site = site

        # Clear the cache
        NavTreeCache.invalidate()

        result = get_nav_context(current_page)

        # Should return a NavTreeContext
        assert isinstance(result, NavTreeContext)
        # Should have accessible root via dict-style access
        root = result["root"]
        # Root should have children attribute (empty for empty site)
        assert hasattr(root, "children")
        assert root.children == []
