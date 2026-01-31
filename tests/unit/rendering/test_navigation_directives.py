"""
Test navigation directives (breadcrumbs, siblings, prev-next, related).

These directives leverage the pre-computed site tree via page context passed to parse_with_context().
"""

from pathlib import Path
from unittest.mock import Mock


class TestBreadcrumbsDirective:
    """Test the breadcrumbs directive."""

    def _create_mock_section(self, title, url, path):
        """Create a mock section for breadcrumbs."""
        section = Mock()
        section.title = title
        section.path = Path(path)
        section.index_page = Mock()
        section.index_page.href = url
        return section

    def test_breadcrumbs_renders_ancestors(self, parser):
        """Test breadcrumbs renders ancestor sections."""

        section1 = self._create_mock_section("Content", "/docs/content/", "docs/content")
        section2 = self._create_mock_section("Docs", "/docs/", "docs")

        current_page = Mock()
        current_page.title = "Authoring"
        current_page.source_path = Path("docs/content/authoring/_index.md")
        current_page.ancestors = [section1, section2]

        content = """
:::{breadcrumbs}
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        assert "breadcrumbs" in result
        assert "Docs" in result
        assert "Content" in result
        assert "Authoring" in result

    def test_breadcrumbs_with_home_link(self, parser):
        """Test breadcrumbs includes home link."""

        current_page = Mock()
        current_page.title = "Test"
        current_page.ancestors = []

        content = """
:::{breadcrumbs}
:show-home: true
:home-text: Home
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        assert "Home" in result
        assert 'href="/"' in result

    def test_breadcrumbs_custom_separator(self, parser):
        """Test breadcrumbs uses custom separator."""

        current_page = Mock()
        current_page.title = "Test"
        current_page.ancestors = []

        content = """
:::{breadcrumbs}
:separator: /
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        assert "breadcrumb-separator" in result

    def test_breadcrumbs_no_page_context(self, parser):
        """Test breadcrumbs handles missing page context."""
        content = """
:::{breadcrumbs}
:::
"""
        # Pass empty context (no page) to test missing page handling
        result = parser.parse_with_context(content, {}, {})

        assert "No page context" in result


class TestSiblingsDirective:
    """Test the siblings directive."""

    def test_siblings_renders_section_pages(self, parser):
        """Test siblings renders other pages in section."""

        sibling1 = Mock()
        sibling1.title = "Installation"
        sibling1.url = "/docs/installation/"
        sibling1.source_path = Path("docs/installation.md")
        sibling1.metadata = {"description": "How to install"}

        sibling2 = Mock()
        sibling2.title = "Configuration"
        sibling2.url = "/docs/config/"
        sibling2.source_path = Path("docs/config.md")
        sibling2.metadata = {}

        section = Mock()
        section.sorted_pages = [sibling1, sibling2]
        section.pages = [sibling1, sibling2]

        current_page = Mock()
        current_page.title = "Installation"
        current_page.source_path = Path("docs/installation.md")
        current_page._section = section

        content = """
:::{siblings}
:exclude-current: true
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        assert "siblings-list" in result
        assert "Configuration" in result
        # Current page should be excluded
        assert (
            result.count("Installation") == 0
            or "Installation" not in result.split("Configuration")[0]
        )

    def test_siblings_with_descriptions(self, parser):
        """Test siblings shows descriptions when enabled."""

        sibling = Mock()
        sibling.title = "Config"
        sibling.url = "/config/"
        sibling.source_path = Path("config.md")
        sibling.metadata = {"description": "Configure your site"}

        section = Mock()
        section.sorted_pages = [sibling]
        section.pages = [sibling]

        current_page = Mock()
        current_page.source_path = Path("other.md")
        current_page._section = section

        content = """
:::{siblings}
:show-description: true
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        assert "Configure your site" in result

    def test_siblings_no_section(self, parser):
        """Test siblings handles missing section."""

        current_page = Mock()
        current_page._section = None

        content = """
:::{siblings}
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        assert "No section" in result


class TestPrevNextDirective:
    """Test the prev-next directive."""

    def test_prev_next_renders_navigation(self, parser):
        """Test prev-next renders navigation links."""

        prev_page = Mock()
        prev_page.title = "Installation"
        prev_page.href = "/docs/installation/"

        next_page = Mock()
        next_page.title = "Configuration"
        next_page.href = "/docs/config/"

        current_page = Mock()
        current_page.title = "Quickstart"
        current_page.prev_in_section = prev_page
        current_page.next_in_section = next_page

        content = """
:::{prev-next}
:show-title: true
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        assert "prev-next" in result
        assert "Installation" in result
        assert "Configuration" in result
        assert "← Previous" in result
        assert "Next →" in result

    def test_prev_next_only_prev(self, parser):
        """Test prev-next with only previous page."""

        prev_page = Mock()
        prev_page.title = "Previous"
        prev_page.href = "/prev/"

        current_page = Mock()
        current_page.prev_in_section = prev_page
        current_page.next_in_section = None

        content = """
:::{prev-next}
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        assert "Previous" in result
        assert "next-link disabled" in result

    def test_prev_next_only_next(self, parser):
        """Test prev-next with only next page."""

        next_page = Mock()
        next_page.title = "Next"
        next_page.href = "/next/"

        current_page = Mock()
        current_page.prev_in_section = None
        current_page.next_in_section = next_page

        content = """
:::{prev-next}
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        assert "Next" in result
        assert "prev-link disabled" in result

    def test_prev_next_no_navigation(self, parser):
        """Test prev-next returns empty when no navigation."""

        current_page = Mock()
        current_page.prev_in_section = None
        current_page.next_in_section = None

        content = """
:::{prev-next}
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        # Should return empty string (no navigation needed)
        assert result.strip() == "" or "prev-next" not in result


class TestRelatedDirective:
    """Test the related directive."""

    def test_related_renders_posts(self, parser):
        """Test related renders related posts."""

        related1 = Mock()
        related1.title = "Advanced Config"
        related1.url = "/docs/advanced/"
        related1.tags = ["config"]

        related2 = Mock()
        related2.title = "Theming"
        related2.url = "/docs/theming/"
        related2.tags = ["theme"]

        current_page = Mock()
        current_page.related_posts = [related1, related2]

        content = """
:::{related}
:title: Related Articles
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        assert "related" in result
        assert "Related Articles" in result
        assert "Advanced Config" in result
        assert "Theming" in result

    def test_related_with_tags(self, parser):
        """Test related shows tags when enabled."""

        related = Mock()
        related.title = "Advanced"
        related.href = "/advanced/"
        related.tags = ["python", "config"]

        current_page = Mock()
        current_page.related_posts = [related]

        content = """
:::{related}
:show-tags: true
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        assert "python" in result
        assert "config" in result

    def test_related_respects_limit(self, parser):
        """Test related respects limit option."""

        related_posts = []
        for i in range(10):
            post = Mock()
            post.title = f"Post {i}"
            post.url = f"/post-{i}/"
            post.tags = []
            related_posts.append(post)

        current_page = Mock()
        current_page.related_posts = related_posts

        content = """
:::{related}
:limit: 3
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        # Should only have 3 posts
        assert "Post 0" in result
        assert "Post 1" in result
        assert "Post 2" in result
        assert "Post 3" not in result

    def test_related_no_posts_returns_empty(self, parser):
        """Test related returns empty when no related posts."""

        current_page = Mock()
        current_page.related_posts = []

        content = """
:::{related}
:::
"""
        result = parser.parse_with_context(content, {}, {"page": current_page})

        # Should return empty string
        assert result.strip() == ""
