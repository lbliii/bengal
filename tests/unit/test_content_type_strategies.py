"""
Unit tests for content type strategies.

Tests the strategy pattern implementation for different content types,
ensuring correct sorting, filtering, pagination, and template selection.
"""

from datetime import datetime
from unittest.mock import Mock

from bengal.content_types.registry import CONTENT_TYPE_REGISTRY, detect_content_type, get_strategy
from bengal.content_types.strategies import (
    ApiReferenceStrategy,
    BlogStrategy,
    CliReferenceStrategy,
    DocsStrategy,
    PageStrategy,
    TutorialStrategy,
)


class TestBlogStrategy:
    """Test blog content type strategy."""

    def test_sort_pages_by_date_newest_first(self):
        """Blog posts should be sorted by date, newest first."""
        strategy = BlogStrategy()

        # Create mock pages with different dates
        page1 = Mock(date=datetime(2025, 1, 1), title="Old Post")
        page2 = Mock(date=datetime(2025, 10, 12), title="Newest Post")
        page3 = Mock(date=datetime(2025, 6, 15), title="Middle Post")
        page4 = Mock(date=None, title="No Date Post")  # Should go to end

        pages = [page1, page2, page3, page4]
        sorted_pages = strategy.sort_pages(pages)

        # Assert newest first
        assert sorted_pages[0].title == "Newest Post"
        assert sorted_pages[1].title == "Middle Post"
        assert sorted_pages[2].title == "Old Post"
        assert sorted_pages[3].title == "No Date Post"

    def test_filter_display_pages_excludes_index(self):
        """Blog list should exclude the index page."""
        strategy = BlogStrategy()

        index_page = Mock(title="Blog Index")
        post1 = Mock(title="Post 1")
        post2 = Mock(title="Post 2")

        pages = [index_page, post1, post2]
        filtered = strategy.filter_display_pages(pages, index_page)

        assert len(filtered) == 2
        assert index_page not in filtered
        assert post1 in filtered
        assert post2 in filtered

    def test_allows_pagination(self):
        """Blog should allow pagination."""
        strategy = BlogStrategy()
        assert strategy.allows_pagination is True

    def test_get_template(self):
        """Blog should use blog/list.html template."""
        strategy = BlogStrategy()
        assert strategy.default_template == "blog/list.html"


class TestDocsStrategy:
    """Test documentation content type strategy."""

    def test_sort_pages_by_weight_then_title(self):
        """Docs should be sorted by weight, then alphabetically."""
        strategy = DocsStrategy()

        # Create mock pages with different weights
        page1 = Mock(weight=10, title="Getting Started", metadata={"weight": 10})
        page2 = Mock(weight=20, title="Advanced", metadata={"weight": 20})
        page3 = Mock(weight=10, title="API Reference", metadata={"weight": 10})
        page4 = Mock(weight=999, title="Zzz No Weight", metadata={})

        pages = [page4, page2, page3, page1]
        sorted_pages = strategy.sort_pages(pages)

        # Assert sorted by weight, then alpha
        assert sorted_pages[0].title == "API Reference"  # weight 10, A
        assert sorted_pages[1].title == "Getting Started"  # weight 10, G
        assert sorted_pages[2].title == "Advanced"  # weight 20
        assert sorted_pages[3].title == "Zzz No Weight"  # weight 999

    def test_should_not_paginate(self):
        """Docs should never paginate."""
        strategy = DocsStrategy()
        assert strategy.allows_pagination is False

    def test_get_template(self):
        """Docs should use doc/list.html template."""
        strategy = DocsStrategy()
        assert strategy.default_template == "doc/list.html"


class TestApiReferenceStrategy:
    """Test API reference content type strategy."""

    def test_sort_pages_keeps_original_order(self):
        """API reference should keep original discovery order."""
        strategy = ApiReferenceStrategy()

        page1 = Mock(title="zebra_function")
        page2 = Mock(title="alpha_class")
        page3 = Mock(title="beta_module")

        pages = [page1, page2, page3]
        sorted_pages = strategy.sort_pages(pages)

        # Should maintain input order
        assert sorted_pages[0].title == "zebra_function"
        assert sorted_pages[1].title == "alpha_class"
        assert sorted_pages[2].title == "beta_module"

    def test_should_not_paginate(self):
        """API reference should never paginate."""
        strategy = ApiReferenceStrategy()
        assert strategy.allows_pagination is False

    def test_get_template(self):
        """API reference should use api-reference/list.html template."""
        strategy = ApiReferenceStrategy()
        assert strategy.default_template == "api-reference/list.html"


class TestCliReferenceStrategy:
    """Test CLI reference content type strategy."""

    def test_get_template(self):
        """CLI reference should use cli-reference/list.html template."""
        strategy = CliReferenceStrategy()
        assert strategy.default_template == "cli-reference/list.html"


class TestTutorialStrategy:
    """Test tutorial content type strategy."""

    def test_sort_pages_by_weight_then_title(self):
        """Tutorials should be sorted by weight for learning order."""
        strategy = TutorialStrategy()

        page1 = Mock(weight=20, title="Advanced Tutorial", metadata={"weight": 20})
        page2 = Mock(weight=10, title="Beginner Tutorial", metadata={"weight": 10})

        pages = [page1, page2]
        sorted_pages = strategy.sort_pages(pages)

        assert sorted_pages[0].title == "Beginner Tutorial"
        assert sorted_pages[1].title == "Advanced Tutorial"


class TestPageStrategy:
    """Test generic page/list content type strategy."""

    def test_sort_pages_by_weight_then_title(self):
        """Generic lists should use weight + title sorting."""
        strategy = PageStrategy()

        page1 = Mock(weight=999, title="Page Z", metadata={})
        page2 = Mock(weight=10, title="Page A", metadata={"weight": 10})

        pages = [page1, page2]
        sorted_pages = strategy.sort_pages(pages)

        assert sorted_pages[0].title == "Page A"
        assert sorted_pages[1].title == "Page Z"

    def test_get_template(self):
        """Generic page should use index.html template."""
        strategy = PageStrategy()
        assert strategy.default_template == "index.html"


class TestContentTypeRegistry:
    """Test content type registry and detection."""

    def test_registry_contains_all_types(self):
        """Registry should have all standard content types."""
        assert "blog" in CONTENT_TYPE_REGISTRY
        assert "doc" in CONTENT_TYPE_REGISTRY
        assert "api-reference" in CONTENT_TYPE_REGISTRY
        assert "cli-reference" in CONTENT_TYPE_REGISTRY
        assert "tutorial" in CONTENT_TYPE_REGISTRY
        assert "list" in CONTENT_TYPE_REGISTRY

    def test_get_strategy_returns_correct_instance(self):
        """get_strategy should return the right strategy class."""
        assert isinstance(get_strategy("blog"), BlogStrategy)
        assert isinstance(get_strategy("doc"), DocsStrategy)
        assert isinstance(get_strategy("api-reference"), ApiReferenceStrategy)
        assert isinstance(get_strategy("cli-reference"), CliReferenceStrategy)
        assert isinstance(get_strategy("tutorial"), TutorialStrategy)
        assert isinstance(get_strategy("list"), PageStrategy)

    def test_get_strategy_fallback_to_page(self):
        """Unknown content types should fall back to page strategy."""
        strategy = get_strategy("unknown-type")
        assert isinstance(strategy, PageStrategy)


class TestContentTypeDetection:
    """Test automatic content type detection from sections."""

    def test_detect_explicit_content_type(self):
        """Explicit content_type in metadata should take priority."""
        section = Mock()
        section.name = "docs"
        section.metadata = {"content_type": "tutorial"}
        section.parent = None
        section.pages = []

        assert detect_content_type(section) == "tutorial"

    def test_detect_from_section_name_blog(self):
        """Section named 'blog' should be detected as blog type."""
        section = Mock()
        section.name = "blog"
        section.metadata = {}
        section.parent = None
        section.pages = []

        assert detect_content_type(section) == "blog"

    def test_detect_from_section_name_api(self):
        """Section named 'api' should be detected as api-reference."""
        for name in ["api", "reference", "api-reference", "api-docs"]:
            section = Mock()
            section.name = name
            section.metadata = {}
            section.parent = None
            section.pages = []
            assert detect_content_type(section) == "api-reference"

    def test_detect_from_section_name_cli(self):
        """Section named 'cli' should be detected as cli-reference."""
        for name in ["cli", "commands", "cli-reference"]:
            section = Mock()
            section.name = name
            section.metadata = {}
            section.parent = None
            section.pages = []
            assert detect_content_type(section) == "cli-reference"

    def test_detect_from_parent_cascade(self):
        """Content type should cascade from parent section."""
        parent = Mock()
        parent.metadata = {"cascade": {"type": "tutorial"}}

        section = Mock()
        section.name = "lesson-1"
        section.metadata = {}
        section.parent = parent
        section.pages = []

        assert detect_content_type(section) == "tutorial"

    def test_detect_from_page_metadata(self):
        """Pages with dates should indicate blog type."""
        page1 = Mock()
        page1.metadata = {"date": "2025-01-01"}
        page1.date = datetime.now()

        page2 = Mock()
        page2.metadata = {"date": "2025-01-02"}
        page2.date = datetime.now()

        page3 = Mock()
        page3.metadata = {"date": "2025-01-03"}
        page3.date = datetime.now()

        section = Mock()
        section.name = "articles"
        section.metadata = {}
        section.parent = None
        section.pages = [page1, page2, page3]

        assert detect_content_type(section) == "blog"

    def test_detect_default_to_list(self):
        """Unknown sections should default to list."""
        section = Mock()
        section.name = "misc"
        section.metadata = {}
        section.parent = None
        section.pages = []

        assert detect_content_type(section) == "list"
