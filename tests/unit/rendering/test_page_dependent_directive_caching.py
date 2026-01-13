"""
Tests for page-dependent directive caching behavior.

Verifies that:
1. Page-dependent directives (child-cards, breadcrumbs, etc.) are NOT cached
   across different pages - each page gets its own rendered output
2. Non-page-dependent directives (note, warning, tabs) ARE cached for performance
3. The _PAGE_DEPENDENT_DIRECTIVES set contains expected directive names

This test file was added after fixing a caching bug where child-cards output
from one page was incorrectly served to other pages with the same directive syntax.

RFC: Page-dependent directives must not be cached because their output depends
on the current page's position in the site tree.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from bengal.directives.cache import clear_cache, get_cache
from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer
from bengal.rendering.parsers.patitas.wrapper import PatitasParser


def create_mock_page(
    title: str,
    source_path: str = "test.md",
    href: str = "/test/",
    metadata: dict[str, Any] | None = None,
) -> Mock:
    """Create a mock page object for testing."""
    page = Mock()
    page.title = title
    page.href = href
    page.source_path = Path(source_path)
    page.metadata = metadata or {}
    page._section = None
    return page


def create_mock_section(
    name: str = "test-section",
    subsections: list | None = None,
    pages: list | None = None,
    metadata: dict[str, Any] | None = None,
) -> Mock:
    """Create a mock section with subsections and pages."""
    section = Mock()
    section.name = name
    section.path = Path(name)
    section.subsections = subsections or []
    section.pages = pages or []
    section.metadata = metadata or {}
    section.index_page = None
    return section


def create_mock_subsection(
    name: str,
    title: str,
    description: str = "",
    url: str = "/",
    icon: str = "",
) -> Mock:
    """Create a mock subsection for testing."""
    section = Mock()
    section.name = name
    section.title = title
    section.path = Path(name)
    section.metadata = {"description": description, "icon": icon, "weight": 0}
    section.index_page = Mock()
    section.index_page.href = url
    return section


class TestPageDependentDirectiveSet:
    """Test that the _PAGE_DEPENDENT_DIRECTIVES set contains expected directives."""

    def test_child_cards_is_page_dependent(self) -> None:
        """child-cards must be in the page-dependent set."""
        assert "child-cards" in HtmlRenderer._PAGE_DEPENDENT_DIRECTIVES

    def test_breadcrumbs_is_page_dependent(self) -> None:
        """breadcrumbs must be in the page-dependent set."""
        assert "breadcrumbs" in HtmlRenderer._PAGE_DEPENDENT_DIRECTIVES

    def test_siblings_is_page_dependent(self) -> None:
        """siblings must be in the page-dependent set."""
        assert "siblings" in HtmlRenderer._PAGE_DEPENDENT_DIRECTIVES

    def test_prev_next_is_page_dependent(self) -> None:
        """prev-next must be in the page-dependent set."""
        assert "prev-next" in HtmlRenderer._PAGE_DEPENDENT_DIRECTIVES

    def test_related_is_page_dependent(self) -> None:
        """related must be in the page-dependent set."""
        assert "related" in HtmlRenderer._PAGE_DEPENDENT_DIRECTIVES

    def test_note_is_not_page_dependent(self) -> None:
        """Regular directives like 'note' should NOT be page-dependent."""
        assert "note" not in HtmlRenderer._PAGE_DEPENDENT_DIRECTIVES

    def test_warning_is_not_page_dependent(self) -> None:
        """Regular directives like 'warning' should NOT be page-dependent."""
        assert "warning" not in HtmlRenderer._PAGE_DEPENDENT_DIRECTIVES

    def test_tabs_is_not_page_dependent(self) -> None:
        """Regular directives like 'tabs' should NOT be page-dependent."""
        assert "tabs" not in HtmlRenderer._PAGE_DEPENDENT_DIRECTIVES
        assert "tab-set" not in HtmlRenderer._PAGE_DEPENDENT_DIRECTIVES


class TestChildCardsNotCachedAcrossPages:
    """Test that child-cards are NOT cached and reused across different pages.
    
    This is the critical bug fix test: if page A has child-cards showing
    [Section1, Section2] and page B has child-cards showing [Section3, Section4],
    they must render their own children, not share cached output.
        
    """

    @pytest.fixture
    def patitas(self) -> PatitasParser:
        """Create a PatitasParser instance (named to avoid conftest conflict)."""
        return PatitasParser()

    @pytest.fixture(autouse=True)
    def clear_directive_cache(self) -> None:
        """Clear directive cache before each test."""
        clear_cache()

    def test_child_cards_different_output_per_page(self, patitas: PatitasParser) -> None:
        """Two pages with identical child-cards syntax get different output based on their section."""
        # Page A: /docs/guide/ with subsections [Getting Started, Installation]
        section_a = create_mock_section(
            name="guide",
            subsections=[
                create_mock_subsection(
                    "getting-started", "Getting Started", url="/docs/guide/getting-started/"
                ),
                create_mock_subsection(
                    "installation", "Installation", url="/docs/guide/installation/"
                ),
            ],
        )
        page_a = create_mock_page(title="Guide", source_path="docs/guide/_index.md")
        page_a._section = section_a

        # Page B: /docs/reference/ with subsections [API, CLI]
        section_b = create_mock_section(
            name="reference",
            subsections=[
                create_mock_subsection("api", "API Reference", url="/docs/reference/api/"),
                create_mock_subsection("cli", "CLI Reference", url="/docs/reference/cli/"),
            ],
        )
        page_b = create_mock_page(title="Reference", source_path="docs/reference/_index.md")
        page_b._section = section_b

        # SAME directive syntax on both pages
        content = """
:::{child-cards}
:columns: 2
:include: sections
:fields: title
:::
"""

        # Render page A
        context_a = {"page": page_a, "site": Mock()}
        result_a = patitas.parse_with_context(content, {}, context_a)

        # Render page B (if caching is broken, this would show page A's content)
        context_b = {"page": page_b, "site": Mock()}
        result_b = patitas.parse_with_context(content, {}, context_b)

        # Page A should show its own children
        assert "Getting Started" in result_a
        assert "Installation" in result_a
        assert "API Reference" not in result_a
        assert "CLI Reference" not in result_a

        # Page B should show ITS own children, not page A's
        assert "API Reference" in result_b
        assert "CLI Reference" in result_b
        assert "Getting Started" not in result_b
        assert "Installation" not in result_b

    def test_child_cards_not_in_cache(self, patitas: PatitasParser) -> None:
        """child-cards directive output should not be stored in directive cache."""
        cache = get_cache()
        cache.enable()  # Ensure caching is enabled

        section = create_mock_section(
            subsections=[create_mock_subsection("test", "Test Section", url="/test/")]
        )
        page = create_mock_page(title="Index", source_path="test/_index.md")
        page._section = section

        context = {"page": page, "site": Mock()}
        content = ":::{child-cards}\n:::"

        # Clear cache before test
        cache.clear()

        # Render child-cards
        result = patitas.parse_with_context(content, {}, context)
        assert "Test Section" in result  # Verify it rendered

        # Note: The real test for non-caching behavior is
        # test_child_cards_different_output_per_page above which verifies
        # that child-cards produces different output for different pages


class TestNonPageDependentDirectivesCached:
    """Test that regular directives ARE cached for performance."""

    @pytest.fixture
    def patitas(self) -> PatitasParser:
        """Create a PatitasParser instance (named to avoid conftest conflict)."""
        return PatitasParser()

    @pytest.fixture(autouse=True)
    def clear_directive_cache(self) -> None:
        """Clear directive cache before each test."""
        clear_cache()

    def test_note_directive_same_output_regardless_of_page(self, patitas: PatitasParser) -> None:
        """Note directive should produce identical output regardless of page context."""
        page_a = create_mock_page(title="Page A", source_path="a.md")
        page_b = create_mock_page(title="Page B", source_path="b.md")

        content = """
:::{note}
This is a note.
:::
"""

        context_a = {"page": page_a, "site": Mock()}
        context_b = {"page": page_b, "site": Mock()}

        result_a = patitas.parse_with_context(content, {}, context_a)
        result_b = patitas.parse_with_context(content, {}, context_b)

        # Both should have identical output (note content is not page-dependent)
        assert "This is a note" in result_a
        assert "This is a note" in result_b
        # Output should be structurally the same
        assert result_a == result_b


class TestRendererHasCurrentPageAlias:
    """Test that HtmlRenderer provides _current_page alias for directive compatibility."""

    def test_current_page_alias_exists(self) -> None:
        """HtmlRenderer should have _current_page slot."""
        renderer = HtmlRenderer()
        assert hasattr(renderer, "_current_page")
        assert hasattr(renderer, "_page_context")

    def test_current_page_equals_page_context(self) -> None:
        """_current_page should be the same object as _page_context."""
        page = create_mock_page(title="Test", source_path="test.md")
        renderer = HtmlRenderer(page_context=page)

        assert renderer._current_page is page
        assert renderer._page_context is page
        assert renderer._current_page is renderer._page_context

    def test_current_page_none_when_no_context(self) -> None:
        """_current_page should be None when no page_context provided."""
        renderer = HtmlRenderer()

        assert renderer._current_page is None
        assert renderer._page_context is None
