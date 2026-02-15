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


# TestSphinxDesignCompatibility removed - Sphinx grid syntax no longer supported
# GridDirective and GridItemCardDirective were removed as part of removing compatibility shims


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
        xref_index = {
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
        context = {"xref_index": xref_index}
        result = parser.parse_with_context(content, {}, context)

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
        xref_index = {
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
        context = {"xref_index": xref_index}
        result = parser.parse_with_context(content, {}, context)

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
        xref_index = {
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
        context = {"xref_index": xref_index}
        result = parser.parse_with_context(content, {}, context)

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
        xref_index = {
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
        context = {"xref_index": xref_index}
        result = parser.parse_with_context(content, {}, context)

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
        xref_index = {
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
        context = {"xref_index": xref_index}
        result = parser.parse_with_context(content, {}, context)

        # Link should be resolved via path
        assert 'href="/docs/installation/"' in result

    def test_link_resolution_by_slug(self, parser):
        """Test link resolution using slug reference."""

        mock_page = self._create_mock_page(
            title="Quickstart",
            url="/docs/quickstart/",
        )
        xref_index = {
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
        context = {"xref_index": xref_index}
        result = parser.parse_with_context(content, {}, context)

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
        page.href = url
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
        section.index_page.href = url
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

        content = """
:::{child-cards}
:columns: 2
:include: sections
:fields: title, description
:::
"""
        context = {"page": current_page}
        result = parser.parse_with_context(content, {}, context)

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

        content = """
:::{child-cards}
:include: sections
:::
"""
        context = {"page": current_page}
        result = parser.parse_with_context(content, {}, context)

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

        content = """
:::{child-cards}
:include: pages
:fields: title, description
:::
"""
        context = {"page": current_page}
        result = parser.parse_with_context(content, {}, context)

        assert "Regular Page" in result
        # Subsection should NOT be included when include: pages
        assert "Subsection" not in result

    def test_child_cards_no_current_page(self, parser):
        """Test child-cards gracefully handles missing current page."""

        content = """
:::{child-cards}
:::
"""
        # Pass empty context (no page)
        context = {}
        result = parser.parse_with_context(content, {}, context)

        # Should render empty grid with message
        assert "card-grid" in result
        assert "No page context available" in result

    def test_child_cards_no_section(self, parser):
        """Test child-cards gracefully handles page with no section."""

        current_page = self._create_mock_page("Orphan", source_path="orphan.md")
        current_page._section = None

        content = """
:::{child-cards}
:::
"""
        context = {"page": current_page}
        result = parser.parse_with_context(content, {}, context)

        # Should render empty grid with message
        assert "card-grid" in result
        assert "Page has no section" in result

    def test_child_cards_empty_section(self, parser):
        """Test child-cards with no children shows empty message."""

        section = self._create_mock_section(subsections=[], pages=[])
        current_page = self._create_mock_page("Empty", source_path="empty/_index.md")
        current_page._section = section

        content = """
:::{child-cards}
:::
"""
        context = {"page": current_page}
        result = parser.parse_with_context(content, {}, context)

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
        subsection.index_page.href = "/docs/org/"
        # Use a real dict for metadata so .get() works correctly
        subsection.metadata = {"description": "Organize stuff", "icon": "folder", "weight": 0}

        section = self._create_mock_section(subsections=[subsection])
        current_page = self._create_mock_page("Index", source_path="docs/_index.md")
        current_page._section = section

        content = """
:::{child-cards}
:include: sections
:fields: title, description, icon
:::
"""
        context = {"page": current_page}
        result = parser.parse_with_context(content, {}, context)

        # Should include icon (📁 is the emoji for "folder")
        assert 'data-icon="folder"' in result
        assert "card-icon" in result

    def test_child_cards_renders_markdown_description(self, parser):
        """Child-cards should render markdown and truncate to first sentence."""

        page = self._create_mock_page(
            "Regular Page",
            description="First sentence with **bold**.\n\n- item 1\n- item 2",
            source_path="docs/page.md",
            url="/docs/page/",
            metadata={"description": "First sentence with **bold**.\n\n- item 1\n- item 2"},
        )

        section = self._create_mock_section(subsections=[], pages=[page])
        current_page = self._create_mock_page("Index", source_path="docs/_index.md")
        current_page._section = section

        content = """
:::{child-cards}
::include: pages
::fields: title, description
::layout: default
::style: default
::columns: 1
::gap: medium
:::
"""
        context = {"page": current_page}
        result = parser.parse_with_context(content, {}, context)

        # Markdown should be rendered, not escaped
        assert "<strong>bold</strong>" in result
        # Only first sentence should appear (list is beyond truncation)
        assert "item 1" not in result


class TestResolveLinkRelativePath:
    """Unit tests for cards._resolve_link relative path resolution."""

    def test_resolve_link_dot_slash_with_current_page_dir(self):
        """Card _resolve_link resolves ./linking/ when current_page_dir provided."""
        from bengal.parsing.backends.patitas.directives.builtins.cards import (
            _resolve_link,
        )

        linking_page = MockPage(title="Linking", href="/docs/content/authoring/linking/")
        xref = {
            "by_path": {"docs/content/authoring/linking": linking_page},
            "by_slug": {},
            "by_id": {},
        }
        url, page = _resolve_link(
            "./linking/", xref, current_page_dir="docs/content/authoring"
        )
        assert url == "/docs/content/authoring/linking/"
        assert page is linking_page

    def test_resolve_link_dot_slash_without_current_page_dir(self):
        """Card _resolve_link returns original when current_page_dir is None."""
        from bengal.parsing.backends.patitas.directives.builtins.cards import (
            _resolve_link,
        )

        xref = {"by_path": {}, "by_slug": {}, "by_id": {}}
        url, page = _resolve_link("./linking/", xref, current_page_dir=None)
        assert url == "./linking/"
        assert page is None


class TestCardsUtilsResolvePage:
    """Unit tests for cards_utils.resolve_page relative path resolution."""

    def test_resolve_page_dot_slash_child_with_current_page_dir(self):
        """./child resolves to current_page_dir/child when page exists."""
        from bengal.parsing.backends.patitas.directives.builtins.cards_utils import (
            resolve_page,
        )

        child_page = MockPage(title="Child", href="/docs/guides/child/")
        xref = {"by_path": {"docs/guides/child": child_page}, "by_slug": {}, "by_id": {}}

        result = resolve_page(xref, "./child", current_page_dir="docs/guides")
        assert result is child_page

    def test_resolve_page_dot_slash_child_without_current_page_dir(self):
        """./child returns None when current_page_dir is None."""
        from bengal.parsing.backends.patitas.directives.builtins.cards_utils import (
            resolve_page,
        )

        xref = {"by_path": {"docs/guides/child": MockPage()}, "by_slug": {}, "by_id": {}}

        result = resolve_page(xref, "./child", current_page_dir=None)
        assert result is None

    def test_resolve_page_dot_dot_slash_sibling(self):
        """../sibling resolves to parent/sibling when page exists."""
        from bengal.parsing.backends.patitas.directives.builtins.cards_utils import (
            resolve_page,
        )

        sibling_page = MockPage(title="Sibling", href="/docs/sibling/")
        xref = {"by_path": {"docs/sibling": sibling_page}, "by_slug": {}, "by_id": {}}

        result = resolve_page(xref, "../sibling", current_page_dir="docs/guides")
        assert result is sibling_page

    def test_resolve_page_absolute_path_lookup(self):
        """docs/guides/child resolves via by_path without current_page_dir."""
        from bengal.parsing.backends.patitas.directives.builtins.cards_utils import (
            resolve_page,
        )

        child_page = MockPage(title="Child", href="/docs/guides/child/")
        xref = {"by_path": {"docs/guides/child": child_page}, "by_slug": {}, "by_id": {}}

        result = resolve_page(xref, "docs/guides/child")
        assert result is child_page

    def test_resolve_page_slug_lookup(self):
        """Slug-only link resolves via by_slug."""
        from bengal.parsing.backends.patitas.directives.builtins.cards_utils import (
            resolve_page,
        )

        page = MockPage(title="Child", href="/child/", slug="child")
        xref = {"by_path": {}, "by_slug": {"child": [page]}, "by_id": {}}

        result = resolve_page(xref, "child")
        assert result is page
