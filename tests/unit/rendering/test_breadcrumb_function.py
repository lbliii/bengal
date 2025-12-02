"""
Tests for breadcrumb template function.
"""

from unittest.mock import Mock

from bengal.rendering.template_functions.navigation import get_breadcrumbs


class TestGetBreadcrumbs:
    """Test the get_breadcrumbs() template function."""

    def test_no_ancestors_returns_empty(self):
        """Pages without ancestors return empty list."""
        page = Mock()
        page.ancestors = []

        result = get_breadcrumbs(page)

        assert result == []

    def test_no_ancestors_attribute_returns_empty(self):
        """Pages without ancestors attribute return empty list."""
        page = Mock(spec=["title", "relative_url"])

        result = get_breadcrumbs(page)

        assert result == []

    def test_basic_breadcrumbs(self):
        """Basic breadcrumb generation with ancestors."""
        # Create mock ancestors
        docs_section = Mock()
        docs_section.title = "Docs"
        docs_section.relative_url = "/docs/"

        page = Mock()
        page.ancestors = [docs_section]
        page.relative_url = "/docs/getting-started/"
        page.title = "Getting Started"

        result = get_breadcrumbs(page)

        # Only 2 items: parent section + current page (no Home)
        assert len(result) == 2
        assert result[0] == {"title": "Docs", "url": "/docs/", "is_current": False}
        assert result[1] == {
            "title": "Getting Started",
            "url": "/docs/getting-started/",
            "is_current": True,
        }

    def test_nested_breadcrumbs(self):
        """Multiple levels of nesting - limited to last 2 ancestors."""
        # Create nested ancestors
        docs = Mock()
        docs.title = "Docs"
        docs.relative_url = "/docs/"

        markdown = Mock()
        markdown.title = "Markdown"
        markdown.relative_url = "/docs/markdown/"

        page = Mock()
        page.ancestors = [markdown, docs]  # Closest ancestor first
        page.relative_url = "/docs/markdown/syntax/"
        page.title = "Syntax"

        result = get_breadcrumbs(page)

        # Limited to 2 ancestors max + current (no Home, 3 items total)
        assert len(result) == 3
        assert result[0]["title"] == "Docs"
        assert result[1]["title"] == "Markdown"
        assert result[2]["title"] == "Syntax"
        assert result[2]["is_current"]

    def test_section_index_page_no_duplication(self):
        """Section index pages don't duplicate the section name."""
        # Create section
        markdown = Mock()
        markdown.title = "Markdown"
        markdown.relative_url = "/docs/markdown/"

        docs = Mock()
        docs.title = "Docs"
        docs.relative_url = "/docs/"

        # Page is the index of the markdown section
        page = Mock()
        page.ancestors = [markdown, docs]
        page.relative_url = "/docs/markdown/"  # Same URL as last ancestor
        page.title = "Markdown"

        result = get_breadcrumbs(page)

        # Should NOT have duplicate "Markdown" at the end (no Home)
        assert len(result) == 2
        assert result[0]["title"] == "Docs"
        assert result[1]["title"] == "Markdown"
        assert result[1]["is_current"]  # Last item is current

        # Verify no duplicate
        titles = [item["title"] for item in result]
        assert titles.count("Markdown") == 1

    def test_all_items_have_required_fields(self):
        """All breadcrumb items have title, url, and is_current."""
        section = Mock()
        section.title = "Docs"
        section.relative_url = "/docs/"

        page = Mock()
        page.ancestors = [section]
        page.relative_url = "/docs/page/"
        page.title = "Page"

        result = get_breadcrumbs(page)

        for item in result:
            assert "title" in item
            assert "url" in item
            assert "is_current" in item
            assert isinstance(item["title"], str)
            assert isinstance(item["url"], str)
            assert isinstance(item["is_current"], bool)

    def test_only_last_item_is_current(self):
        """Only the last breadcrumb item is marked as current."""
        section = Mock()
        section.title = "Docs"
        section.relative_url = "/docs/"

        page = Mock()
        page.ancestors = [section]
        page.relative_url = "/docs/page/"
        page.title = "Page"

        result = get_breadcrumbs(page)

        # Check that only last item is current
        for i, item in enumerate(result):
            if i == len(result) - 1:
                assert item["is_current"]
            else:
                assert not item["is_current"]

    def test_ancestor_without_url_uses_slug(self):
        """Ancestors without relative_url property fall back to slug."""
        section = Mock()
        section.title = "Docs"
        section.slug = "docs"
        # No relative_url attribute
        del section.relative_url

        page = Mock()
        page.ancestors = [section]
        page.relative_url = "/docs/page/"
        page.title = "Page"

        result = get_breadcrumbs(page)

        # Should construct URL from slug (no Home, so index 0)
        assert result[0]["url"] == "/docs/"

    def test_page_without_title_shows_untitled(self):
        """Pages without title show 'Untitled' when no slug or URL path available."""
        # Use spec to prevent Mock from auto-creating title attribute
        section = Mock(spec=["relative_url", "slug"])
        section.relative_url = "/"  # Root URL has empty url_parts, triggering "Untitled" fallback
        section.slug = None  # No slug either to trigger "Untitled"

        page = Mock()
        page.ancestors = [section]
        page.relative_url = "/page/"
        page.title = "Page"

        result = get_breadcrumbs(page)

        # No Home, so index 0 is the untitled section
        assert result[0]["title"] == "Untitled"

    def test_deeply_nested_truncates_to_2_ancestors(self):
        """Deep nesting is truncated to only last 2 ancestors."""
        # Create deeply nested ancestors (4 levels)
        root = Mock()
        root.title = "Root"
        root.relative_url = "/root/"

        level1 = Mock()
        level1.title = "Level1"
        level1.relative_url = "/root/level1/"

        level2 = Mock()
        level2.title = "Level2"
        level2.relative_url = "/root/level1/level2/"

        level3 = Mock()
        level3.title = "Level3"
        level3.relative_url = "/root/level1/level2/level3/"

        page = Mock()
        page.ancestors = [level3, level2, level1, root]  # Closest ancestor first
        page.relative_url = "/root/level1/level2/level3/page/"
        page.title = "Page"

        result = get_breadcrumbs(page)

        # Should only include last 2 ancestors + current page (3 items total)
        assert len(result) == 3
        assert result[0]["title"] == "Level2"  # Grandparent
        assert result[1]["title"] == "Level3"  # Parent
        assert result[2]["title"] == "Page"    # Current
        assert result[2]["is_current"]
