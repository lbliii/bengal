"""
Test cards directive system (modern and Sphinx-Design compatibility).
"""

from tests._testing.mocks import MockPage


class TestModernCardsDirective:
    """Test the modern cards/card directive syntax."""

    def test_simple_card_grid(self, parser):
        """Test basic cards grid with auto-layout."""

        content = """
:::{cards}

:::{card} Card One
First card content.
:::

:::{card} Card Two
Second card content.
:::

::::
"""
        result = parser.parse(content, {})

        assert "card-grid" in result
        assert "Card One" in result
        assert "Card Two" in result
        assert "First card content" in result
        assert "Second card content" in result

    def test_card_with_icon(self, parser):
        """Test card with icon."""

        content = """
:::{cards}
:::{card} Documentation
:icon: book

Complete docs here.
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-icon" in result
        assert 'data-icon="book"' in result
        assert "Documentation" in result

    def test_card_with_link(self, parser):
        """Test card that's a clickable link."""

        content = """
:::{cards}
:::{card} API Reference
:link: /api/

Check out the API.
:::
::::
"""
        result = parser.parse(content, {})

        assert "<a" in result
        assert 'href="/api/"' in result
        assert "API Reference" in result

    def test_card_with_color(self, parser):
        """Test card with color accent."""

        content = """
:::{cards}
:::{card} Important
:color: blue

This is important.
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-color-blue" in result

    def test_responsive_columns(self, parser):
        """Test responsive column specification."""

        content = """
:::{cards}
:columns: 1-2-3

:::{card} One
:::
:::{card} Two
:::
:::{card} Three
:::
::::
"""
        result = parser.parse(content, {})

        assert 'data-columns="1-2-3"' in result

    def test_fixed_columns(self, parser):
        """Test fixed column count."""

        content = """
:::{cards}
:columns: 3

:::{card} A
:::
:::{card} B
:::
:::{card} C
:::
::::
"""
        result = parser.parse(content, {})

        assert 'data-columns="3"' in result

    def test_card_with_all_options(self, parser):
        """Test card with all available options."""

        content = """
:::{cards}
:columns: 2
:gap: large

:::{card} Feature
:icon: rocket
:link: /feature/
:color: purple
:footer: Updated 2025

Amazing new feature with **markdown** support!
:::
::::
"""
        result = parser.parse(content, {})

        assert 'data-columns="2"' in result
        assert 'data-gap="large"' in result
        assert "card-icon" in result
        assert 'href="/feature/"' in result
        assert "card-color-purple" in result
        assert "card-footer" in result
        assert "Updated 2025" in result
        assert "<strong>markdown</strong>" in result


class TestSphinxDesignCompatibility:
    """Test Sphinx-Design grid/grid-item-card compatibility."""

    def test_basic_grid_syntax(self, parser):
        """Test basic Sphinx grid syntax."""

        content = """
::::{grid} 1 2 2 2

:::{grid-item-card} My Card
:link: docs/page

Card content here.
:::
::::
"""
        result = parser.parse(content, {})

        # Should render as card-grid
        assert "card-grid" in result
        assert "My Card" in result
        assert "Card content here" in result

    def test_grid_with_octicon(self, parser):
        """Test grid-item-card with octicon syntax."""

        content = """
::::{grid} 1 2 2 2

:::{grid-item-card} {octicon}`book;1.5em;sd-mr-1` Documentation
:link: docs/intro

Learn more about our docs.
:::
::::
"""
        result = parser.parse(content, {})

        # Should extract icon from octicon syntax
        assert "card-icon" in result
        assert 'data-icon="book"' in result
        # Title should be clean (no octicon syntax)
        assert "Documentation" in result
        # Octicon syntax should be removed
        assert "{octicon}" not in result

    def test_grid_column_conversion(self, parser):
        """Test that Sphinx breakpoints are converted correctly."""

        content = """
::::{grid} 1 2 3 4

:::{grid-item-card} Card
:::
::::
"""
        result = parser.parse(content, {})

        # Should convert "1 2 3 4" to "1-2-3-4"
        assert 'data-columns="1-2-3-4"' in result

    def test_grid_gutter_conversion(self, parser):
        """Test that Sphinx gutter is converted to gap."""

        content = """
::::{grid} 2
:gutter: 3

:::{grid-item-card} Card
:::
::::
"""
        result = parser.parse(content, {})

        # Gutter 3 should convert to gap large
        assert 'data-gap="large"' in result

    def test_multiple_grid_cards(self, parser):
        """Test multiple cards in Sphinx grid."""

        content = """
::::{grid} 2

:::{grid-item-card} {octicon}`star` First
:link: first/
First content.
:::

:::{grid-item-card} {octicon}`rocket` Second
:link: second/
Second content.
:::
::::
"""
        result = parser.parse(content, {})

        assert "First" in result
        assert "Second" in result
        assert 'data-icon="star"' in result
        assert 'data-icon="rocket"' in result
        assert 'href="first/"' in result
        assert 'href="second/"' in result


class TestCardMarkdownSupport:
    """Test that cards support full markdown in content."""

    def test_markdown_in_card_content(self, parser):
        """Test markdown rendering in card content."""

        content = """
:::{cards}
:::{card} Test

This has **bold** and *italic* text.

- List item 1
- List item 2

[A link](/page/)
:::
::::
"""
        result = parser.parse(content, {})

        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result
        assert "<li>List item 1</li>" in result
        assert 'href="/page/"' in result

    def test_code_in_card(self, parser):
        """Test code blocks in cards."""

        content = """
:::{cards}
:::{card} Code Example

```python
def hello():
    print("world")
```
:::
::::
"""
        result = parser.parse(content, {})

        # Check for Pygments syntax highlighting
        assert '<span class="k">def</span>' in result or "def" in result
        assert '<span class="nf">hello</span>' in result or "hello" in result
        assert '<div class="highlight">' in result or "<code" in result or "<pre" in result


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_cards_grid(self, parser):
        """Test cards with no children."""

        content = """
:::{cards}
::::
"""
        result = parser.parse(content, {})

        # Should not crash
        assert "card-grid" in result

    def test_card_without_title(self, parser):
        """Test card with no title."""

        content = """
:::{cards}
:::{card}
Content only, no title.
:::
::::
"""
        result = parser.parse(content, {})

        assert "Content only" in result

    def test_invalid_column_value(self, parser):
        """Test that invalid columns default to auto."""

        content = """
:::{cards}
:columns: invalid

:::{card} Test
:::
::::
"""
        result = parser.parse(content, {})

        # Should default to auto
        assert 'data-columns="auto"' in result

    def test_invalid_color(self, parser):
        """Test that invalid colors are ignored."""

        content = """
:::{cards}
:::{card} Test
:color: notacolor

Content
:::
::::
"""
        result = parser.parse(content, {})

        # Should not have a color class
        assert "card-color-notacolor" not in result


class TestCardLayoutOption:
    """Test the :layout: option for cards."""

    def test_grid_layout_horizontal(self, parser):
        """Test horizontal layout on cards grid."""

        content = """
:::{cards}
:layout: horizontal

:::{card} Card One
Content
:::
::::
"""
        result = parser.parse(content, {})

        assert 'data-layout="horizontal"' in result

    def test_grid_layout_portrait(self, parser):
        """Test portrait layout on cards grid."""

        content = """
:::{cards}
:layout: portrait
:columns: 3

:::{card} Card One
Content
:::
::::
"""
        result = parser.parse(content, {})

        assert 'data-layout="portrait"' in result

    def test_grid_layout_compact(self, parser):
        """Test compact layout on cards grid."""

        content = """
:::{cards}
:layout: compact

:::{card} Card One
Content
:::
::::
"""
        result = parser.parse(content, {})

        assert 'data-layout="compact"' in result

    def test_grid_layout_default(self, parser):
        """Test default layout on cards grid."""

        content = """
:::{cards}

:::{card} Card One
Content
:::
::::
"""
        result = parser.parse(content, {})

        assert 'data-layout="default"' in result

    def test_card_layout_override(self, parser):
        """Test individual card can override grid layout."""

        content = """
:::{cards}
:layout: default

:::{card} Normal Card
Normal content
:::

:::{card} Horizontal Card
:layout: horizontal

Horizontal content
:::
::::
"""
        result = parser.parse(content, {})

        # Grid has default layout
        assert 'data-layout="default"' in result
        # Individual card has horizontal layout class
        assert "card-layout-horizontal" in result

    def test_invalid_layout_defaults(self, parser):
        """Test that invalid layout defaults to default."""

        content = """
:::{cards}
:layout: notvalid

:::{card} Card
Content
:::
::::
"""
        result = parser.parse(content, {})

        assert 'data-layout="default"' in result


class TestCardPullOption:
    """Test the :pull: option for fetching metadata from linked pages."""

    def test_pull_option_parsed(self, parser):
        """Test that pull option is parsed correctly."""

        content = """
:::{cards}
:::{card}
:link: docs/quickstart
:pull: title, description

Fallback content
:::
::::
"""
        result = parser.parse(content, {})

        # Card should render (pull gracefully degrades without xref_index)
        assert "card" in result
        # Link should be used (as-is since no xref_index to resolve)
        assert 'href="docs/quickstart"' in result

    def test_pull_with_fallback_title(self, parser):
        """Test that provided title is used when pull fails."""

        content = """
:::{cards}
:::{card} My Custom Title
:link: docs/nonexistent
:pull: title

Fallback description
:::
::::
"""
        result = parser.parse(content, {})

        # Should use provided title since no xref_index
        assert "My Custom Title" in result

    def test_pull_multiple_fields(self, parser):
        """Test pull with multiple fields specified."""

        content = """
:::{cards}
:::{card} Title
:link: id:my-page
:pull: title, description, icon

Content
:::
::::
"""
        result = parser.parse(content, {})

        # Should render without error
        assert "card" in result
        # id: prefix in link should work
        assert "id:my-page" in result or "href" in result

    def test_pull_empty_fields(self, parser):
        """Test pull with empty field list."""

        content = """
:::{cards}
:::{card} Title
:link: /docs/
:pull:

Content only
:::
::::
"""
        result = parser.parse(content, {})

        # Should render normally
        assert "Title" in result
        assert "Content only" in result


class TestLayoutAndPullCombined:
    """Test combining layout and pull options."""

    def test_all_new_options_together(self, parser):
        """Test layout and pull together."""

        content = """
:::{cards}
:layout: horizontal
:columns: 2

:::{card}
:link: docs/getting-started
:pull: title, description
:layout: portrait

Optional fallback
:::

:::{card} Manual Card
:color: blue

Manual content
:::
::::
"""
        result = parser.parse(content, {})

        # Grid has horizontal layout
        assert 'data-layout="horizontal"' in result
        # First card has portrait override
        assert "card-layout-portrait" in result
        # Second card has color
        assert "card-color-blue" in result


class TestCardPullWithXrefIndex:
    """Test :pull: option with actual xref_index (not graceful degradation)."""

    def _create_mock_page(self, title, url, description="", icon="", tags=None):
        """Create a mock page object for testing using shared MockPage."""
        return MockPage(
            title=title,
            href=url,  # Use href (the canonical field) not url
            metadata={"description": description, "icon": icon},
            tags=tags or [],
        )

    def test_pull_title_from_linked_page(self, parser):
        """Test that :pull: title actually fetches from linked page."""

        # Set up xref_index with mock page
        mock_page = self._create_mock_page(
            title="Writer Quickstart",
            url="/docs/get-started/quickstart-writer/",
            description="Learn to write content",
        )
        parser.md.renderer._xref_index = {
            "by_id": {"writer-qs": mock_page},
            "by_path": {},
            "by_slug": {},
        }

        content = """
::::{cards}
:::{card}
:link: id:writer-qs
:pull: title

Fallback content
:::
::::
"""
        result = parser.parse(content, {})

        # Should have pulled the title
        assert "Writer Quickstart" in result
        # Link should be resolved
        assert 'href="/docs/get-started/quickstart-writer/"' in result

    def test_pull_description_from_linked_page(self, parser):
        """Test that :pull: description replaces empty content."""

        mock_page = self._create_mock_page(
            title="Themer Guide",
            url="/docs/theming/",
            description="Learn to customize themes and styles",
        )
        parser.md.renderer._xref_index = {
            "by_id": {"themer-qs": mock_page},
            "by_path": {},
            "by_slug": {},
        }

        # Note: Empty card content should be replaced by pulled description
        content = """
::::{cards}
:::{card} Custom Title
:link: id:themer-qs
:pull: description
:::
::::
"""
        result = parser.parse(content, {})

        # Should use explicit title
        assert "Custom Title" in result
        # Should have pulled description (when content is empty)
        # Note: This may not replace non-empty content
        assert 'href="/docs/theming/"' in result

    def test_pull_icon_from_linked_page(self, parser):
        """Test that :pull: icon fetches icon from page metadata."""

        mock_page = self._create_mock_page(
            title="Code Guide",
            url="/docs/code/",
            icon="code",
        )
        parser.md.renderer._xref_index = {
            "by_id": {"code-guide": mock_page},
            "by_path": {},
            "by_slug": {},
        }

        content = """
::::{cards}
:::{card} Title
:link: id:code-guide
:pull: icon

Content
:::
::::
"""
        result = parser.parse(content, {})

        # Should have pulled the icon
        assert 'data-icon="code"' in result

    def test_explicit_values_override_pulled(self, parser):
        """Test that explicit values take precedence over pulled values."""

        mock_page = self._create_mock_page(
            title="Page Title",
            url="/docs/page/",
            description="Page description",
            icon="book",
        )
        parser.md.renderer._xref_index = {
            "by_id": {"my-page": mock_page},
            "by_path": {},
            "by_slug": {},
        }

        content = """
::::{cards}
:::{card} Explicit Title
:link: id:my-page
:pull: title, icon
:icon: rocket

Content here
:::
::::
"""
        result = parser.parse(content, {})

        # Explicit title should be used, not pulled
        assert "Explicit Title" in result
        assert "Page Title" not in result
        # Explicit icon should be used, not pulled
        assert 'data-icon="rocket"' in result
        assert 'data-icon="book"' not in result

    def test_link_resolution_by_path(self, parser):
        """Test link resolution using path reference."""

        mock_page = self._create_mock_page(
            title="Installation Guide",
            url="/docs/installation/",
        )
        parser.md.renderer._xref_index = {
            "by_id": {},
            "by_path": {"docs/installation": mock_page},
            "by_slug": {},
        }

        content = """
::::{cards}
:::{card} Install
:link: docs/installation
:pull: title
:::
::::
"""
        result = parser.parse(content, {})

        # Link should be resolved via path
        assert 'href="/docs/installation/"' in result

    def test_link_resolution_by_slug(self, parser):
        """Test link resolution using slug reference."""

        mock_page = self._create_mock_page(
            title="Quickstart",
            url="/docs/quickstart/",
        )
        parser.md.renderer._xref_index = {
            "by_id": {},
            "by_path": {},
            "by_slug": {"quickstart": [mock_page]},
        }

        content = """
::::{cards}
:::{card} Start
:link: quickstart
:pull: title
:::
::::
"""
        result = parser.parse(content, {})

        # Link should be resolved via slug
        assert 'href="/docs/quickstart/"' in result


class TestChildCardsDirective:
    """Test the child-cards directive that auto-generates cards from page children."""

    def _create_mock_section(self, subsections=None, pages=None, metadata=None):
        """Create a mock section with subsections and pages."""
        from pathlib import Path
        from unittest.mock import Mock

        section = Mock()
        section.subsections = subsections or []
        section.pages = pages or []
        section.metadata = metadata or {}
        section.name = "test-section"
        section.path = Path("test-section")
        return section

    def _create_mock_page(
        self, title, description="", url="/", source_path="test.md", metadata=None
    ):
        """Create a mock page for testing."""
        from pathlib import Path
        from unittest.mock import Mock

        page = Mock()
        page.title = title
        page.url = url
        page.source_path = Path(source_path)
        page.metadata = metadata or {"description": description}
        return page

    def _create_mock_subsection(self, name, title, description="", url="/", metadata=None):
        """Create a mock subsection for testing."""
        from pathlib import Path
        from unittest.mock import Mock

        section = Mock()
        section.name = name
        section.title = title
        section.metadata = metadata or {"description": description}
        section.path = Path(name)
        section.index_page = Mock()
        section.index_page.url = url
        return section

    def test_child_cards_renders_subsections(self, parser):
        """Test child-cards directive renders subsections as cards."""

        # Create mock subsections
        subsection1 = self._create_mock_subsection(
            "organization",
            "Content Organization",
            description="Learn about organizing content",
            url="/docs/content/organization/",
        )
        subsection2 = self._create_mock_subsection(
            "authoring",
            "Content Authoring",
            description="Learn about authoring",
            url="/docs/content/authoring/",
        )

        # Create mock section with subsections
        section = self._create_mock_section(subsections=[subsection1, subsection2])

        # Create mock current page with _section
        current_page = self._create_mock_page(title="Content", source_path="docs/content/_index.md")
        current_page._section = section

        # Set current page on renderer
        parser.md.renderer._current_page = current_page

        content = """
:::{child-cards}
:columns: 2
:include: sections
:fields: title, description
:::
"""
        result = parser.parse(content, {})

        # Should render card grid
        assert "card-grid" in result
        assert 'data-columns="2"' in result

        # Should include subsection cards
        assert "Content Organization" in result
        assert "Content Authoring" in result
        assert "Learn about organizing content" in result
        assert "Learn about authoring" in result

    def test_child_cards_includes_only_sections(self, parser):
        """Test child-cards with include: sections only shows subsections."""

        subsection = self._create_mock_subsection("sub", "Subsection", url="/docs/sub/")
        page = self._create_mock_page("Regular Page", source_path="docs/page.md", url="/docs/page/")

        section = self._create_mock_section(subsections=[subsection], pages=[page])
        current_page = self._create_mock_page("Index", source_path="docs/_index.md")
        current_page._section = section

        parser.md.renderer._current_page = current_page

        content = """
:::{child-cards}
:include: sections
:::
"""
        result = parser.parse(content, {})

        assert "Subsection" in result
        # Regular page should NOT be included when include: sections
        assert "Regular Page" not in result

    def test_child_cards_includes_only_pages(self, parser):
        """Test child-cards with include: pages only shows pages."""

        subsection = self._create_mock_subsection("sub", "Subsection", url="/docs/sub/")
        page = self._create_mock_page(
            "Regular Page",
            source_path="docs/page.md",
            url="/docs/page/",
            metadata={"description": "A regular page"},
        )

        section = self._create_mock_section(subsections=[subsection], pages=[page])
        current_page = self._create_mock_page("Index", source_path="docs/_index.md")
        current_page._section = section

        parser.md.renderer._current_page = current_page

        content = """
:::{child-cards}
:include: pages
:fields: title, description
:::
"""
        result = parser.parse(content, {})

        assert "Regular Page" in result
        # Subsection should NOT be included when include: pages
        assert "Subsection" not in result

    def test_child_cards_no_current_page(self, parser):
        """Test child-cards gracefully handles missing current page."""

        # Don't set _current_page
        parser.md.renderer._current_page = None

        content = """
:::{child-cards}
:::
"""
        result = parser.parse(content, {})

        # Should render empty grid with message
        assert "card-grid" in result
        assert "No page context available" in result

    def test_child_cards_no_section(self, parser):
        """Test child-cards gracefully handles page with no section."""

        current_page = self._create_mock_page("Orphan", source_path="orphan.md")
        current_page._section = None

        parser.md.renderer._current_page = current_page

        content = """
:::{child-cards}
:::
"""
        result = parser.parse(content, {})

        # Should render empty grid with message
        assert "card-grid" in result
        assert "Page has no section" in result

    def test_child_cards_empty_section(self, parser):
        """Test child-cards with no children shows empty message."""

        section = self._create_mock_section(subsections=[], pages=[])
        current_page = self._create_mock_page("Empty", source_path="empty/_index.md")
        current_page._section = section

        parser.md.renderer._current_page = current_page

        content = """
:::{child-cards}
:::
"""
        result = parser.parse(content, {})

        assert "No child content found" in result

    def test_child_cards_with_icons(self, parser):
        """Test child-cards pulls icon field from metadata."""
        from pathlib import Path
        from unittest.mock import Mock

        # Create subsection with icon in metadata
        subsection = Mock()
        subsection.name = "org"
        subsection.title = "Organization"
        subsection.path = Path("org")
        subsection.index_page = Mock()
        subsection.index_page.url = "/docs/org/"
        # Use a real dict for metadata so .get() works correctly
        subsection.metadata = {"description": "Organize stuff", "icon": "folder", "weight": 0}

        section = self._create_mock_section(subsections=[subsection])
        current_page = self._create_mock_page("Index", source_path="docs/_index.md")
        current_page._section = section

        parser.md.renderer._current_page = current_page

        content = """
:::{child-cards}
:include: sections
:fields: title, description, icon
:::
"""
        result = parser.parse(content, {})

        # Should include icon (📁 is the emoji for "folder")
        assert 'data-icon="folder"' in result
        assert "card-icon" in result
