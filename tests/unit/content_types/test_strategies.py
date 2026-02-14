"""
Unit tests for content type strategies.

Tests the strategy pattern implementation for different content types,
ensuring correct sorting, filtering, pagination, and template selection.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from bengal.content_types.registry import CONTENT_TYPE_REGISTRY, detect_content_type, get_strategy
from bengal.content_types.strategies import (
    ApiReferenceStrategy,
    BlogStrategy,
    ChangelogStrategy,
    CliReferenceStrategy,
    DocsStrategy,
    NotebookStrategy,
    PageStrategy,
    TrackStrategy,
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

    def test_get_template_backward_compat(self):
        """Blog should use blog/list.html template when called without params."""
        strategy = BlogStrategy()
        assert strategy.get_template() == "blog/list.html"

    def test_get_template_for_section_index(self):
        """Blog section index should use blog/list.html template."""
        from pathlib import Path
        from unittest.mock import Mock

        strategy = BlogStrategy()
        page = Mock()
        page.is_home = False
        page.url = "/blog/"
        page.source_path = Path("/content/blog/_index.md")

        template_engine = Mock()
        template_engine.env = Mock()
        template_engine.env.get_template = Mock(return_value=Mock())

        result = strategy.get_template(page, template_engine)
        assert result == "blog/list.html"

    def test_get_template_for_home_page(self):
        """Blog home page should try blog/home.html first."""
        from pathlib import Path
        from unittest.mock import Mock

        strategy = BlogStrategy()
        page = Mock()
        page.is_home = True
        page.url = "/"
        page.source_path = Path("/content/_index.md")

        template_engine = Mock()
        template_engine.env = Mock()

        # Mock template_exists to return True for blog/home.html
        def mock_get_template(name):
            if name == "blog/home.html":
                return Mock()
            raise Exception("Not found")

        template_engine.env.get_template = mock_get_template

        result = strategy.get_template(page, template_engine)
        assert result == "blog/home.html"


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

    def test_get_template_backward_compat(self):
        """Docs should use doc/list.html template when called without params."""
        strategy = DocsStrategy()
        assert strategy.get_template() == "doc/list.html"

    def test_get_template_for_section_index(self):
        """Docs section index should use doc/list.html template."""
        from pathlib import Path
        from unittest.mock import Mock

        strategy = DocsStrategy()
        page = Mock()
        page.is_home = False
        page.url = "/docs/"
        page.source_path = Path("/content/docs/_index.md")

        template_engine = Mock()
        template_engine.env = Mock()
        template_engine.env.get_template = Mock(return_value=Mock())

        result = strategy.get_template(page, template_engine)
        assert result == "doc/list.html"


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

    def test_get_template_backward_compat(self):
        """API reference should use autodoc/python/list.html template when called without params."""
        strategy = ApiReferenceStrategy()
        assert strategy.get_template() == "autodoc/python/list.html"


class TestCliReferenceStrategy:
    """Test CLI reference content type strategy."""

    def test_get_template_backward_compat(self):
        """CLI reference should use autodoc/cli/list.html template when called without params."""
        strategy = CliReferenceStrategy()
        assert strategy.get_template() == "autodoc/cli/list.html"


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

    def test_get_template_backward_compat(self):
        """Generic page should use index.html template when called without params."""
        strategy = PageStrategy()
        assert strategy.get_template() == "index.html"


class TestContentTypeRegistry:
    """Test content type registry and detection."""

    def test_registry_contains_all_types(self):
        """Registry should have all standard content types."""
        assert "blog" in CONTENT_TYPE_REGISTRY
        assert "doc" in CONTENT_TYPE_REGISTRY
        assert "autodoc-python" in CONTENT_TYPE_REGISTRY
        assert "autodoc-cli" in CONTENT_TYPE_REGISTRY
        assert "tutorial" in CONTENT_TYPE_REGISTRY
        assert "notebook" in CONTENT_TYPE_REGISTRY
        assert "list" in CONTENT_TYPE_REGISTRY

    @pytest.mark.parametrize(
        "content_type,expected_strategy_class",
        [
            ("blog", BlogStrategy),
            ("doc", DocsStrategy),
            ("autodoc-python", ApiReferenceStrategy),
            ("autodoc-cli", CliReferenceStrategy),
            ("tutorial", TutorialStrategy),
            ("notebook", NotebookStrategy),
            ("list", PageStrategy),
        ],
        ids=["blog", "doc", "autodoc-python", "autodoc-cli", "tutorial", "notebook", "list"],
    )
    def test_get_strategy_returns_correct_instance(self, content_type, expected_strategy_class):
        """
        get_strategy should return the correct strategy class for each content type.

        Ensures that the registry correctly maps content type names to their
        corresponding strategy implementations.
        """
        strategy = get_strategy(content_type)
        assert isinstance(strategy, expected_strategy_class), (
            f"get_strategy('{content_type}') should return {expected_strategy_class.__name__}, "
            f"got {type(strategy).__name__}"
        )

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

    @pytest.mark.parametrize(
        "section_name",
        ["api", "reference", "autodoc-python", "api-docs"],
        ids=["api", "reference", "autodoc-python", "api-docs"],
    )
    def test_detect_from_section_name_api(self, section_name):
        """
        Section names for API documentation should be detected as autodoc-python.

        Tests common naming conventions for API documentation sections to ensure
        automatic content type detection works across different naming styles.
        """
        section = Mock()
        section.name = section_name
        section.metadata = {}
        section.parent = None
        section.pages = []

        detected = detect_content_type(section)
        assert detected == "autodoc-python", (
            f"Section name '{section_name}' should be detected as 'autodoc-python', "
            f"but was detected as '{detected}'"
        )

    @pytest.mark.parametrize(
        "section_name",
        ["cli", "commands", "autodoc-cli"],
        ids=["cli", "commands", "autodoc-cli"],
    )
    def test_detect_from_section_name_cli(self, section_name):
        """
        Section names for CLI documentation should be detected as autodoc-cli.

        Tests common naming conventions for CLI documentation sections to ensure
        automatic content type detection works across different naming styles.
        """
        section = Mock()
        section.name = section_name
        section.metadata = {}
        section.parent = None
        section.pages = []

        detected = detect_content_type(section)
        assert detected == "autodoc-cli", (
            f"Section name '{section_name}' should be detected as 'autodoc-cli', "
            f"but was detected as '{detected}'"
        )

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

    @pytest.mark.parametrize(
        "section_name",
        ["changelog", "releases", "release-notes", "releasenotes", "changes"],
        ids=["changelog", "releases", "release-notes", "releasenotes", "changes"],
    )
    def test_detect_from_section_name_changelog(self, section_name):
        """
        Section names for changelogs should be detected as changelog type.

        Tests common naming conventions for changelog/release sections to ensure
        automatic content type detection works across different naming styles.
        """
        section = Mock()
        section.name = section_name
        section.metadata = {}
        section.parent = None
        section.pages = []

        detected = detect_content_type(section)
        assert detected == "changelog", (
            f"Section name '{section_name}' should be detected as 'changelog', "
            f"but was detected as '{detected}'"
        )


class TestChangelogStrategy:
    """Test changelog content type strategy."""

    def test_sort_pages_by_date_newest_first(self):
        """Changelog releases should be sorted by date, newest first."""
        strategy = ChangelogStrategy()

        page1 = Mock(date=datetime(2025, 1, 1), title="v1.0.0")
        page2 = Mock(date=datetime(2025, 6, 15), title="v1.1.0")
        page3 = Mock(date=datetime(2025, 10, 12), title="v2.0.0")
        page4 = Mock(date=None, title="v0.1.0")  # Should go to end

        pages = [page1, page2, page3, page4]
        sorted_pages = strategy.sort_pages(pages)

        assert sorted_pages[0].title == "v2.0.0"
        assert sorted_pages[1].title == "v1.1.0"
        assert sorted_pages[2].title == "v1.0.0"
        assert sorted_pages[3].title == "v0.1.0"

    def test_should_not_paginate(self):
        """Changelog should not paginate."""
        strategy = ChangelogStrategy()
        assert strategy.allows_pagination is False

    def test_get_template_backward_compat(self):
        """Changelog should use changelog/list.html template when called without params."""
        strategy = ChangelogStrategy()
        assert strategy.get_template() == "changelog/list.html"


class TestTrackStrategy:
    """Test learning track content type strategy."""

    def test_sort_pages_by_weight_then_title(self):
        """Tracks should be sorted by weight for learning order."""
        strategy = TrackStrategy()

        page1 = Mock(weight=20, title="Advanced Module", metadata={"weight": 20})
        page2 = Mock(weight=10, title="Beginner Module", metadata={"weight": 10})
        page3 = Mock(weight=10, title="Another Beginner", metadata={"weight": 10})

        pages = [page1, page2, page3]
        sorted_pages = strategy.sort_pages(pages)

        assert sorted_pages[0].title == "Another Beginner"  # weight 10, A
        assert sorted_pages[1].title == "Beginner Module"  # weight 10, B
        assert sorted_pages[2].title == "Advanced Module"  # weight 20

    def test_should_not_paginate(self):
        """Tracks should not paginate."""
        strategy = TrackStrategy()
        assert strategy.allows_pagination is False

    def test_get_template_backward_compat(self):
        """Track should use tracks/list.html template when called without params."""
        strategy = TrackStrategy()
        assert strategy.get_template() == "tracks/list.html"

    def test_get_template_for_section_index(self):
        """Track section index should use tracks/list.html with cascade fallback."""
        from pathlib import Path

        strategy = TrackStrategy()
        page = Mock()
        page.is_home = False
        page._path = "/tracks/"
        page.source_path = Path("/content/tracks/_index.md")

        template_engine = Mock()
        template_engine.template_exists = lambda name: name == "tracks/list.html"

        result = strategy.get_template(page, template_engine)
        assert result == "tracks/list.html"

    def test_get_template_for_home_page(self):
        """Track strategy should handle home pages with proper cascade."""
        from pathlib import Path

        strategy = TrackStrategy()
        page = Mock()
        page.is_home = True
        page._path = "/"
        page.source_path = Path("/content/_index.md")

        template_engine = Mock()
        template_engine.template_exists = lambda name: name == "tracks/home.html"

        result = strategy.get_template(page, template_engine)
        assert result == "tracks/home.html"


class TestNotebookStrategy:
    """Test notebook content type strategy."""

    def test_sort_pages_by_weight_then_title(self) -> None:
        """Notebooks should be sorted by weight, then title."""
        strategy = NotebookStrategy()

        page1 = Mock(weight=20, title="Advanced Notebook", metadata={"weight": 20})
        page2 = Mock(weight=10, title="Intro Notebook", metadata={"weight": 10})
        page3 = Mock(weight=10, title="Another Intro", metadata={"weight": 10})

        pages = [page1, page2, page3]
        sorted_pages = strategy.sort_pages(pages)

        assert sorted_pages[0].title == "Another Intro"
        assert sorted_pages[1].title == "Intro Notebook"
        assert sorted_pages[2].title == "Advanced Notebook"

    def test_should_not_paginate(self) -> None:
        """Notebooks should not paginate."""
        strategy = NotebookStrategy()
        assert strategy.allows_pagination is False

    def test_get_template_backward_compat(self) -> None:
        """Notebook should use notebook/single.html template when called without params."""
        strategy = NotebookStrategy()
        assert strategy.get_template() == "notebook/single.html"

    @pytest.mark.parametrize(
        "section_name",
        ["notebooks", "notebook", "examples"],
        ids=["notebooks", "notebook", "examples"],
    )
    def test_detect_from_section_name(self, section_name: str) -> None:
        """Section names for notebooks should be detected as notebook type."""
        section = Mock()
        section.name = section_name
        section.metadata = {}
        section.parent = None
        section.pages = []

        detected = detect_content_type(section)
        assert detected == "notebook", (
            f"Section name '{section_name}' should be detected as 'notebook', "
            f"but was detected as '{detected}'"
        )


class TestSingletonBehavior:
    """Test that the registry properly uses singleton pattern."""

    def test_get_strategy_returns_singleton_for_unknown_types(self):
        """Unknown types should return the same PageStrategy singleton, not new instances."""
        s1 = get_strategy("unknown-type-1")
        s2 = get_strategy("unknown-type-2")
        s3 = get_strategy("completely-made-up")

        assert s1 is s2, "Should return same singleton for different unknown types"
        assert s2 is s3, "Should return same singleton consistently"
        assert s1 is CONTENT_TYPE_REGISTRY["page"], "Should use registered page singleton"

    def test_get_strategy_returns_registry_singletons(self):
        """get_strategy should return the exact same instances as in registry."""
        for content_type in [
            "blog",
            "doc",
            "autodoc-python",
            "autodoc-cli",
            "tutorial",
            "changelog",
            "notebook",
        ]:
            retrieved = get_strategy(content_type)
            registered = CONTENT_TYPE_REGISTRY[content_type]
            assert retrieved is registered, f"{content_type} should return exact registry singleton"

    def test_registry_list_and_page_are_both_page_strategy(self):
        """'list' and 'page' content types should both be PageStrategy instances."""
        # Both are PageStrategy but are separate instances (not aliases)
        list_strategy = CONTENT_TYPE_REGISTRY["list"]
        page_strategy = CONTENT_TYPE_REGISTRY["page"]
        assert isinstance(list_strategy, PageStrategy), "'list' should be PageStrategy"
        assert isinstance(page_strategy, PageStrategy), "'page' should be PageStrategy"


class TestTemplateCascadeFallback:
    """Test that template resolution properly falls back when templates are missing."""

    def test_blog_falls_back_when_specific_missing(self):
        """Blog should fall back to generic templates when blog/* don't exist."""
        from pathlib import Path

        strategy = BlogStrategy()
        page = Mock()
        page.is_home = False
        page._path = "/blog/"
        page.source_path = Path("/content/blog/_index.md")

        # Mock engine where blog/list.html doesn't exist but list.html does
        template_engine = Mock()
        template_engine.template_exists = lambda name: name in ["list.html", "index.html"]

        result = strategy.get_template(page, template_engine)
        assert result == "list.html", "Should fall back to generic list.html"

    def test_docs_falls_back_when_specific_missing(self):
        """Docs should fall back to generic templates when doc/* don't exist."""
        from pathlib import Path

        strategy = DocsStrategy()
        page = Mock()
        page.is_home = False
        page._path = "/docs/intro/"
        page.source_path = Path("/content/docs/intro.md")

        # Mock engine where only generic templates exist
        template_engine = Mock()
        template_engine.template_exists = lambda name: name in ["single.html", "page.html"]

        result = strategy.get_template(page, template_engine)
        assert result == "single.html", "Should fall back to generic single.html"

    def test_ultimate_fallback_to_default_template(self):
        """Should return default_template when no candidates exist."""
        from pathlib import Path

        strategy = BlogStrategy()
        page = Mock()
        page.is_home = False
        page._path = "/blog/"
        page.source_path = Path("/content/blog/_index.md")

        # Mock engine where NO templates exist
        template_engine = Mock()
        template_engine.template_exists = lambda name: False

        result = strategy.get_template(page, template_engine)
        assert result == strategy.default_template, "Should fall back to default_template"

    def test_fallback_without_template_engine(self):
        """Should return fallback when template_engine is None."""
        from pathlib import Path

        strategy = ApiReferenceStrategy()
        page = Mock()
        page.is_home = False
        page._path = "/api/"
        page.source_path = Path("/content/api/_index.md")

        result = strategy.get_template(page, None)
        assert result == strategy.default_template, "Should return default when engine is None"

    def test_autodoc_cascade_includes_generic_autodoc(self):
        """Autodoc strategies should try autodoc/* before generic templates."""
        from pathlib import Path

        strategy = ApiReferenceStrategy()
        page = Mock()
        page.is_home = False
        page._path = "/api/"
        page.source_path = Path("/content/api/_index.md")

        # Mock engine where only autodoc/list.html exists (not autodoc/python/list.html)
        template_engine = Mock()
        template_engine.template_exists = lambda name: name == "autodoc/list.html"

        result = strategy.get_template(page, template_engine)
        assert result == "autodoc/list.html", "Should find autodoc/list.html in cascade"


class TestDetectionPriority:
    """Test that detection order handles overlapping cases correctly."""

    def test_autodoc_python_wins_over_doc_for_reference(self):
        """'reference' section should detect as autodoc-python, not doc."""
        section = Mock()
        section.name = "reference"  # Matches both ApiReferenceStrategy and DocsStrategy patterns
        section.metadata = {}
        section.parent = None
        section.pages = []

        # autodoc-python should win because it's checked first in detection order
        result = detect_content_type(section)
        assert result == "autodoc-python", (
            "'reference' should be detected as 'autodoc-python' (higher priority than 'doc')"
        )

    def test_explicit_type_overrides_detection(self):
        """Explicit content_type should override auto-detection even for matching names."""
        section = Mock()
        section.name = "blog"  # Would normally detect as blog
        section.metadata = {"content_type": "doc"}  # But explicit override says doc
        section.parent = None
        section.pages = []

        result = detect_content_type(section)
        assert result == "doc", "Explicit content_type should override name-based detection"

    def test_parent_cascade_overrides_name_detection(self):
        """Parent cascade should override section name detection."""
        parent = Mock()
        parent.metadata = {"cascade": {"type": "tutorial"}}

        section = Mock()
        section.name = "blog"  # Would normally detect as blog
        section.metadata = {}
        section.parent = parent

        result = detect_content_type(section)
        assert result == "tutorial", "Parent cascade should override name-based detection"
