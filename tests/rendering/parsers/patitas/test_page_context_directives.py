"""Tests for patitas directives that require page context.

These tests ensure patitas correctly passes page_context to directives like:
- child-cards: Auto-generates cards from page children
- breadcrumbs: Navigation from page ancestors
- siblings: Other pages in same section
- prev-next: Section-aware navigation

This catches regressions like the placeholder bug where child-cards
output "Child cards will be generated at build time" instead of actual cards.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

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
    page._section = None  # Set by caller if needed
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


class TestChildCardsWithPageContext:
    """Test child-cards directive renders actual cards, not placeholder."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a PatitasParser instance."""
        return PatitasParser()

    def test_child_cards_renders_subsections(self, parser: PatitasParser) -> None:
        """Test child-cards renders actual subsection cards, not placeholder."""
        # Create mock subsections
        subsection1 = create_mock_subsection(
            "organization",
            "Content Organization",
            description="Learn about organizing content",
            url="/docs/content/organization/",
        )
        subsection2 = create_mock_subsection(
            "authoring",
            "Content Authoring",
            description="Learn about authoring",
            url="/docs/content/authoring/",
        )

        # Create section with subsections
        section = create_mock_section(subsections=[subsection1, subsection2])

        # Create current page with _section
        current_page = create_mock_page(
            title="Content",
            source_path="docs/content/_index.md",
        )
        current_page._section = section

        # Build context with page
        context = {"page": current_page, "site": Mock()}

        content = """
:::{child-cards}
:columns: 2
:include: sections
:fields: title, description
:::
"""
        result = parser.parse_with_context(content, {}, context)

        # Should NOT show placeholder
        assert "Child cards will be generated at build time" not in result

        # Should render actual cards
        assert "card-grid" in result
        assert 'data-columns="2"' in result
        assert "Content Organization" in result
        assert "Content Authoring" in result
        assert "Learn about organizing content" in result
        assert "Learn about authoring" in result

    def test_child_cards_no_placeholder_with_empty_section(self, parser: PatitasParser) -> None:
        """Empty section shows 'No child content' not the build-time placeholder."""
        section = create_mock_section(subsections=[], pages=[])
        current_page = create_mock_page(
            title="Empty",
            source_path="empty/_index.md",
        )
        current_page._section = section

        context = {"page": current_page, "site": Mock()}

        content = """:::{child-cards}
:::"""
        result = parser.parse_with_context(content, {}, context)

        # Should show "No child content" not "will be generated"
        assert "No child content found" in result
        assert "Child cards will be generated at build time" not in result

    def test_child_cards_no_page_context_shows_message(self, parser: PatitasParser) -> None:
        """Without page context, shows appropriate message."""
        # No page in context
        context = {"site": Mock()}

        content = """:::{child-cards}
:::"""
        result = parser.parse_with_context(content, {}, context)

        # Should show "No page context" not "will be generated"
        assert "No page context available" in result
        assert "Child cards will be generated at build time" not in result

    def test_child_cards_includes_icons(self, parser: PatitasParser) -> None:
        """Test child-cards renders icon field from metadata."""
        subsection = create_mock_subsection(
            "organization",
            "Organization",
            description="Organize stuff",
            url="/docs/org/",
            icon="folder",
        )

        section = create_mock_section(subsections=[subsection])
        current_page = create_mock_page(
            title="Index",
            source_path="docs/_index.md",
        )
        current_page._section = section

        context = {"page": current_page, "site": Mock()}

        content = """
:::{child-cards}
:include: sections
:fields: title, description, icon
:::
"""
        result = parser.parse_with_context(content, {}, context)

        # Should include icon
        assert 'data-icon="folder"' in result
        assert "card-icon" in result

    def test_child_cards_with_pages_only(self, parser: PatitasParser) -> None:
        """Test child-cards with include: pages filters correctly."""
        subsection = create_mock_subsection("sub", "Subsection", url="/docs/sub/")

        page = create_mock_page(
            title="Regular Page",
            source_path="docs/page.md",
            href="/docs/page/",
            metadata={"description": "A regular page"},
        )

        section = create_mock_section(subsections=[subsection], pages=[page])
        current_page = create_mock_page(
            title="Index",
            source_path="docs/_index.md",
        )
        current_page._section = section

        context = {"page": current_page, "site": Mock()}

        content = """
:::{child-cards}
:include: pages
:fields: title, description
:::
"""
        result = parser.parse_with_context(content, {}, context)

        # Should include page
        assert "Regular Page" in result
        # Should NOT include subsection when include: pages
        assert "Subsection" not in result


class TestParserParityForChildCards:
    """Ensure Mistune and Patitas produce equivalent output for child-cards.

    This parity test would have caught the patitas placeholder bug.
    """

    @pytest.fixture
    def mistune_parser(self):
        """Create a MistuneParser instance."""
        from bengal.rendering.parsers import MistuneParser

        return MistuneParser()

    @pytest.fixture
    def patitas_parser(self) -> PatitasParser:
        """Create a PatitasParser instance."""
        return PatitasParser()

    def test_both_parsers_render_child_cards_not_placeholder(
        self, mistune_parser, patitas_parser
    ) -> None:
        """Both parsers should render actual cards, not placeholder text."""
        subsection = create_mock_subsection(
            "test-section",
            "Test Section",
            description="A test section",
            url="/test/section/",
        )

        section = create_mock_section(subsections=[subsection])
        current_page = create_mock_page(
            title="Index",
            source_path="test/_index.md",
        )
        current_page._section = section

        content = """
:::{child-cards}
:columns: 2
:include: sections
:fields: title, description
:::
"""
        # Mistune uses renderer._current_page
        mistune_parser.md.renderer._current_page = current_page
        mistune_result = mistune_parser.parse(content, {})

        # Patitas uses parse_with_context
        context = {"page": current_page, "site": Mock()}
        patitas_result = patitas_parser.parse_with_context(content, {}, context)

        # Neither should have the placeholder
        assert "Child cards will be generated at build time" not in mistune_result
        assert "Child cards will be generated at build time" not in patitas_result

        # Both should have actual card content
        assert "Test Section" in mistune_result
        assert "Test Section" in patitas_result

        # Both should have card-grid
        assert "card-grid" in mistune_result
        assert "card-grid" in patitas_result
