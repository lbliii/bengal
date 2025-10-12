"""
Tests for navigation template functions.

Tests the data provider functions that handle complex logic for
breadcrumbs, pagination, TOC grouping, and navigation trees.
"""

from unittest.mock import Mock

from bengal.rendering.template_functions.navigation import (
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

    def test_simple_section_with_pages(self):
        """Section with pages builds simple tree."""
        # Create mock pages
        page1 = Mock()
        page1.title = "Page 1"
        page1.url = "/docs/page1/"

        page2 = Mock()
        page2.title = "Page 2"
        page2.url = "/docs/page2/"

        # Create mock section
        section = Mock()
        section.title = "Docs"
        section.url = "/docs/"
        section.index_page = None
        section.regular_pages = [page1, page2]
        section.sections = []

        # Create current page
        current_page = Mock()
        current_page.url = "/docs/page1/"
        current_page._section = section
        current_page.ancestors = [section]

        result = get_nav_tree(current_page, root_section=section)

        assert len(result) == 2
        assert result[0]["title"] == "Page 1"
        assert result[0]["is_current"]
        assert result[0]["depth"] == 0
        assert result[1]["title"] == "Page 2"
        assert not result[1]["is_current"]

    def test_nested_sections(self):
        """Nested sections create hierarchical tree."""
        # Create pages
        page1 = Mock()
        page1.title = "Getting Started"
        page1.url = "/docs/getting-started/"

        subpage = Mock()
        subpage.title = "Advanced Topic"
        subpage.url = "/docs/advanced/topic/"

        # Create subsection
        subsection = Mock()
        subsection.title = "Advanced"
        subsection.url = "/docs/advanced/"
        subsection.index_page = None
        subsection.regular_pages = [subpage]
        subsection.sections = []

        # Create root section
        section = Mock()
        section.title = "Docs"
        section.url = "/docs/"
        section.index_page = None
        section.regular_pages = [page1]
        section.sections = [subsection]

        current_page = Mock()
        current_page.url = "/docs/advanced/topic/"
        current_page._section = subsection
        current_page.ancestors = [subsection, section]

        result = get_nav_tree(current_page, root_section=section)

        assert len(result) == 2  # page1 + subsection
        assert result[0]["title"] == "Getting Started"
        assert result[0]["depth"] == 0

        # Subsection has children
        assert result[1]["title"] == "Advanced"
        assert result[1]["is_section"]
        assert result[1]["has_children"]
        assert len(result[1]["children"]) == 1
        assert result[1]["children"][0]["title"] == "Advanced Topic"
        assert result[1]["children"][0]["depth"] == 1

    def test_active_trail_marking(self):
        """Active trail is marked correctly."""
        # Create pages
        page1 = Mock()
        page1.title = "Page 1"
        page1.url = "/docs/page1/"

        page2 = Mock()
        page2.title = "Page 2"
        page2.url = "/docs/section/page2/"

        subsection = Mock()
        subsection.title = "Section"
        subsection.url = "/docs/section/"
        subsection.index_page = None
        subsection.regular_pages = [page2]
        subsection.sections = []

        section = Mock()
        section.title = "Docs"
        section.url = "/docs/"
        section.index_page = None
        section.regular_pages = [page1]
        section.sections = [subsection]

        current_page = Mock()
        current_page.url = "/docs/section/page2/"
        current_page._section = subsection
        current_page.ancestors = [subsection, section]

        result = get_nav_tree(current_page, root_section=section)

        # page1 not in trail
        assert not result[0]["is_in_active_trail"]

        # subsection in trail
        assert result[1]["is_in_active_trail"]

        # page2 in trail and current
        assert result[1]["children"][0]["is_in_active_trail"]
        assert result[1]["children"][0]["is_current"]

    def test_index_page_included(self):
        """Section index page is included in tree."""
        index_page = Mock()
        index_page.title = "Introduction"
        index_page.url = "/docs/"

        page1 = Mock()
        page1.title = "Page 1"
        page1.url = "/docs/page1/"

        section = Mock()
        section.title = "Docs"
        section.url = "/docs/"
        section.index_page = index_page
        section.regular_pages = [index_page, page1]  # Index page also in regular_pages
        section.sections = []

        current_page = Mock()
        current_page.url = "/docs/page1/"
        current_page._section = section
        current_page.ancestors = [section]

        result = get_nav_tree(current_page, root_section=section)

        # Should have 2 items: index page and page1 (not duplicated)
        assert len(result) == 2
        assert result[0]["title"] == "Introduction"
        assert result[0]["url"] == "/docs/"
        assert result[1]["title"] == "Page 1"

    def test_depth_tracking(self):
        """Depth is tracked correctly for nested structures."""
        # Create 3-level nesting
        page_l3 = Mock()
        page_l3.title = "Deep Page"
        page_l3.url = "/docs/l1/l2/page/"

        section_l2 = Mock()
        section_l2.title = "Level 2"
        section_l2.url = "/docs/l1/l2/"
        section_l2.index_page = None
        section_l2.regular_pages = [page_l3]
        section_l2.sections = []

        section_l1 = Mock()
        section_l1.title = "Level 1"
        section_l1.url = "/docs/l1/"
        section_l1.index_page = None
        section_l1.regular_pages = []
        section_l1.sections = [section_l2]

        section_root = Mock()
        section_root.title = "Docs"
        section_root.url = "/docs/"
        section_root.index_page = None
        section_root.regular_pages = []
        section_root.sections = [section_l1]

        current_page = Mock()
        current_page.url = "/docs/l1/l2/page/"
        current_page._section = section_l2
        current_page.ancestors = [section_l2, section_l1, section_root]

        result = get_nav_tree(current_page, root_section=section_root)

        # Root section
        assert result[0]["depth"] == 0
        # Level 1 section
        l1 = result[0]["children"][0]
        assert l1["depth"] == 1
        # Level 2 section's page
        l2_page = l1["children"][0]
        assert l2_page["depth"] == 2
