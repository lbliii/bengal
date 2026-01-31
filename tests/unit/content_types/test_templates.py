"""
Unit tests for content type template utilities.

Tests the template cascade resolution logic and page classification.
"""

from pathlib import Path
from unittest.mock import Mock

from bengal.content_types.templates import (
    build_template_cascade,
    classify_page,
    resolve_template_cascade,
)


class TestClassifyPage:
    """Test page classification for template resolution."""

    def test_classifies_home_page_by_is_home(self):
        """Page with is_home=True should be classified as 'home'."""
        page = Mock()
        page.is_home = True
        page._path = "/something/"
        page.source_path = Path("/content/something/_index.md")

        assert classify_page(page) == "home"

    def test_classifies_home_page_by_root_path(self):
        """Page with _path='/' should be classified as 'home'."""
        page = Mock()
        page.is_home = False
        page._path = "/"
        page.source_path = Path("/content/_index.md")

        assert classify_page(page) == "home"

    def test_classifies_section_index_as_list(self):
        """Section index (_index.md) should be classified as 'list'."""
        page = Mock()
        page.is_home = False
        page._path = "/blog/"
        page.source_path = Path("/content/blog/_index.md")

        assert classify_page(page) == "list"

    def test_classifies_regular_page_as_single(self):
        """Regular content page should be classified as 'single'."""
        page = Mock()
        page.is_home = False
        page._path = "/blog/my-post/"
        page.source_path = Path("/content/blog/my-post.md")

        assert classify_page(page) == "single"

    def test_home_takes_priority_over_index_stem(self):
        """is_home=True should take priority even if source is _index.md."""
        page = Mock()
        page.is_home = True
        page._path = "/"
        page.source_path = Path("/content/_index.md")

        # Should be "home" not "list"
        assert classify_page(page) == "home"


class TestBuildTemplateCascade:
    """Test template cascade building."""

    def test_builds_cascade_for_home_page(self):
        """Home page cascade should include home.html and index.html variants."""
        result = build_template_cascade("blog", "home")

        assert result == [
            "blog/home.html",
            "blog/index.html",
            "home.html",
            "index.html",
        ]

    def test_builds_cascade_for_list_page(self):
        """List page cascade should include list.html and index.html variants."""
        result = build_template_cascade("doc", "list")

        assert result == [
            "doc/list.html",
            "doc/index.html",
            "list.html",
            "index.html",
        ]

    def test_builds_cascade_for_single_page(self):
        """Single page cascade should include single.html and page.html variants."""
        result = build_template_cascade("tutorial", "single")

        assert result == [
            "tutorial/single.html",
            "tutorial/page.html",
            "single.html",
            "page.html",
        ]

    def test_includes_extra_prefixes(self):
        """Extra prefixes should be included between type-specific and generic."""
        result = build_template_cascade("autodoc/python", "list", ["autodoc"])

        assert result == [
            "autodoc/python/list.html",
            "autodoc/python/index.html",
            "autodoc/list.html",
            "autodoc/index.html",
            "list.html",
            "index.html",
        ]

    def test_multiple_extra_prefixes(self):
        """Multiple extra prefixes should all be included in order."""
        result = build_template_cascade("a/b/c", "single", ["a/b", "a"])

        assert result == [
            "a/b/c/single.html",
            "a/b/c/page.html",
            "a/b/single.html",
            "a/b/page.html",
            "a/single.html",
            "a/page.html",
            "single.html",
            "page.html",
        ]

    def test_no_extra_prefixes_when_none(self):
        """None extra_prefixes should not add any extra entries."""
        result = build_template_cascade("blog", "home", None)

        assert result == [
            "blog/home.html",
            "blog/index.html",
            "home.html",
            "index.html",
        ]

    def test_empty_extra_prefixes_list(self):
        """Empty extra_prefixes list should not add any extra entries."""
        result = build_template_cascade("blog", "home", [])

        assert result == [
            "blog/home.html",
            "blog/index.html",
            "home.html",
            "index.html",
        ]


class TestResolveTemplateCascade:
    """Test resolve_template_cascade utility function."""

    def test_returns_fallback_when_engine_is_none(self):
        """Should return fallback when template_engine is None."""
        result = resolve_template_cascade(
            ["blog/home.html", "home.html"],
            None,
            fallback="index.html",
        )

        assert result == "index.html"

    def test_returns_first_existing_template(self):
        """Should return the first template that exists."""
        engine = Mock()
        # First doesn't exist, second does
        engine.template_exists = Mock(side_effect=[False, True, False])

        result = resolve_template_cascade(
            ["blog/home.html", "home.html", "index.html"],
            engine,
            fallback="default.html",
        )

        assert result == "home.html"

    def test_returns_fallback_when_no_template_exists(self):
        """Should return fallback when no candidates exist."""
        engine = Mock()
        engine.template_exists = Mock(return_value=False)

        result = resolve_template_cascade(
            ["blog/home.html", "home.html"],
            engine,
            fallback="single.html",
        )

        assert result == "single.html"

    def test_checks_candidates_in_order(self):
        """Should check candidates in the provided order."""
        engine = Mock()
        engine.template_exists = Mock(return_value=False)

        resolve_template_cascade(
            ["first.html", "second.html", "third.html"],
            engine,
            fallback="default.html",
        )

        # Verify call order
        calls = engine.template_exists.call_args_list
        assert calls[0][0][0] == "first.html"
        assert calls[1][0][0] == "second.html"
        assert calls[2][0][0] == "third.html"

    def test_stops_at_first_match(self):
        """Should stop checking once a match is found."""
        engine = Mock()
        # First template exists
        engine.template_exists = Mock(side_effect=[True, True, True])

        resolve_template_cascade(
            ["blog/home.html", "home.html", "index.html"],
            engine,
            fallback="default.html",
        )

        # Should only call once since first one matches
        assert engine.template_exists.call_count == 1

    def test_with_empty_candidates_list(self):
        """Should return fallback when candidates list is empty."""
        engine = Mock()
        engine.template_exists = Mock(return_value=True)

        result = resolve_template_cascade(
            [],
            engine,
            fallback="default.html",
        )

        assert result == "default.html"
        engine.template_exists.assert_not_called()

    def test_default_fallback_is_single_html(self):
        """Should use 'single.html' as default fallback."""
        engine = Mock()
        engine.template_exists = Mock(return_value=False)

        result = resolve_template_cascade(
            ["nonexistent.html"],
            engine,
        )

        assert result == "single.html"

    def test_with_typical_blog_cascade(self):
        """Test with typical blog template cascade."""
        engine = Mock()
        # Only index.html exists
        engine.template_exists = Mock(side_effect=[False, False, False, True])

        result = resolve_template_cascade(
            ["blog/home.html", "blog/index.html", "home.html", "index.html"],
            engine,
            fallback="default.html",
        )

        assert result == "index.html"

    def test_with_typical_docs_cascade(self):
        """Test with typical docs template cascade."""
        engine = Mock()
        # doc/list.html exists
        engine.template_exists = Mock(side_effect=[False, True])

        result = resolve_template_cascade(
            ["doc/home.html", "doc/list.html"],
            engine,
            fallback="doc/list.html",
        )

        assert result == "doc/list.html"
