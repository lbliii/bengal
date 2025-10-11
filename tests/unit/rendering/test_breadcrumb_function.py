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
        page = Mock(spec=['title', 'url'])

        result = get_breadcrumbs(page)

        assert result == []

    def test_basic_breadcrumbs(self):
        """Basic breadcrumb generation with ancestors."""
        # Create mock ancestors
        docs_section = Mock()
        docs_section.title = "Docs"
        docs_section.url = "/docs/"

        page = Mock()
        page.ancestors = [docs_section]
        page.url = "/docs/getting-started/"
        page.title = "Getting Started"

        result = get_breadcrumbs(page)

        assert len(result) == 3
        assert result[0] == {'title': 'Home', 'url': '/', 'is_current': False}
        assert result[1] == {'title': 'Docs', 'url': '/docs/', 'is_current': False}
        assert result[2] == {'title': 'Getting Started', 'url': '/docs/getting-started/', 'is_current': True}

    def test_nested_breadcrumbs(self):
        """Multiple levels of nesting."""
        # Create nested ancestors
        docs = Mock()
        docs.title = "Docs"
        docs.url = "/docs/"

        markdown = Mock()
        markdown.title = "Markdown"
        markdown.url = "/docs/markdown/"

        page = Mock()
        page.ancestors = [markdown, docs]  # Closest ancestor first
        page.url = "/docs/markdown/syntax/"
        page.title = "Syntax"

        result = get_breadcrumbs(page)

        assert len(result) == 4
        assert result[0]['title'] == 'Home'
        assert result[1]['title'] == 'Docs'
        assert result[2]['title'] == 'Markdown'
        assert result[3]['title'] == 'Syntax'
        assert result[3]['is_current']

    def test_section_index_page_no_duplication(self):
        """Section index pages don't duplicate the section name."""
        # Create section
        markdown = Mock()
        markdown.title = "Markdown"
        markdown.url = "/docs/markdown/"

        docs = Mock()
        docs.title = "Docs"
        docs.url = "/docs/"

        # Page is the index of the markdown section
        page = Mock()
        page.ancestors = [markdown, docs]
        page.url = "/docs/markdown/"  # Same URL as last ancestor
        page.title = "Markdown"

        result = get_breadcrumbs(page)

        # Should NOT have duplicate "Markdown" at the end
        assert len(result) == 3
        assert result[0]['title'] == 'Home'
        assert result[1]['title'] == 'Docs'
        assert result[2]['title'] == 'Markdown'
        assert result[2]['is_current']  # Last item is current

        # Verify no duplicate
        titles = [item['title'] for item in result]
        assert titles.count('Markdown') == 1

    def test_all_items_have_required_fields(self):
        """All breadcrumb items have title, url, and is_current."""
        section = Mock()
        section.title = "Docs"
        section.url = "/docs/"

        page = Mock()
        page.ancestors = [section]
        page.url = "/docs/page/"
        page.title = "Page"

        result = get_breadcrumbs(page)

        for item in result:
            assert 'title' in item
            assert 'url' in item
            assert 'is_current' in item
            assert isinstance(item['title'], str)
            assert isinstance(item['url'], str)
            assert isinstance(item['is_current'], bool)

    def test_only_last_item_is_current(self):
        """Only the last breadcrumb item is marked as current."""
        section = Mock()
        section.title = "Docs"
        section.url = "/docs/"

        page = Mock()
        page.ancestors = [section]
        page.url = "/docs/page/"
        page.title = "Page"

        result = get_breadcrumbs(page)

        # Check that only last item is current
        for i, item in enumerate(result):
            if i == len(result) - 1:
                assert item['is_current']
            else:
                assert not item['is_current']

    def test_ancestor_without_url_uses_slug(self):
        """Ancestors without url property fall back to slug."""
        section = Mock()
        section.title = "Docs"
        section.slug = "docs"
        # No url attribute
        del section.url

        page = Mock()
        page.ancestors = [section]
        page.url = "/docs/page/"
        page.title = "Page"

        result = get_breadcrumbs(page)

        # Should construct URL from slug
        assert result[1]['url'] == "/docs/"

    def test_page_without_title_shows_untitled(self):
        """Pages without title show 'Untitled'."""
        section = Mock()
        section.url = "/docs/"
        del section.title  # No title

        page = Mock()
        page.ancestors = [section]
        page.url = "/docs/page/"
        page.title = "Page"

        result = get_breadcrumbs(page)

        assert result[1]['title'] == "Untitled"

    def test_home_is_always_first(self):
        """Home is always the first breadcrumb."""
        section = Mock()
        section.title = "Docs"
        section.url = "/docs/"

        page = Mock()
        page.ancestors = [section]
        page.url = "/docs/page/"
        page.title = "Page"

        result = get_breadcrumbs(page)

        assert result[0]['title'] == 'Home'
        assert result[0]['url'] == '/'
        assert not result[0]['is_current']

