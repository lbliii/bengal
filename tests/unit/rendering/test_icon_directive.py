"""
Test icon directive.

Validates inline SVG icon rendering from Bengal's icon library.
"""

from __future__ import annotations

import textwrap


class TestIconDirective:
    """Test icon rendering."""

    def test_basic_icon(self, parser):
        """Test basic icon with no options."""
        markdown = """:::{icon} terminal
:::"""
        result = parser.parse(markdown, {})
        # Should render an SVG
        assert "<svg" in result
        assert "bengal-icon" in result
        assert "icon-terminal" in result

    def test_icon_with_size(self, parser):
        """Test icon with custom size."""
        markdown = """:::{icon} terminal
:size: 32
:::"""
        result = parser.parse(markdown, {})
        assert 'width="32"' in result
        assert 'height="32"' in result

    def test_icon_with_class(self, parser):
        """Test icon with custom CSS class."""
        markdown = """:::{icon} terminal
:class: icon-primary
:::"""
        result = parser.parse(markdown, {})
        assert "icon-primary" in result
        assert "bengal-icon" in result

    def test_icon_with_aria_label(self, parser):
        """Test icon with accessibility label."""
        markdown = """:::{icon} terminal
:aria-label: Terminal command prompt
:::"""
        result = parser.parse(markdown, {})
        assert 'aria-label="Terminal command prompt"' in result
        assert 'role="img"' in result

    def test_icon_without_aria_label_is_hidden(self, parser):
        """Test icon without aria-label is aria-hidden."""
        markdown = """:::{icon} terminal
:::"""
        result = parser.parse(markdown, {})
        assert 'aria-hidden="true"' in result

    def test_icon_all_options(self, parser):
        """Test icon with all options."""
        markdown = """:::{icon} docs
:size: 48
:class: my-custom-class
:aria-label: Documentation icon
:::"""
        result = parser.parse(markdown, {})
        assert 'width="48"' in result
        assert 'height="48"' in result
        assert "my-custom-class" in result
        assert "bengal-icon" in result
        assert "icon-docs" in result
        assert 'aria-label="Documentation icon"' in result

    def test_icon_name_normalization(self, parser):
        """Test icon name is normalized (lowercase, hyphenated)."""
        markdown = """:::{icon} Bengal Rosette
:::"""
        result = parser.parse(markdown, {})
        assert "icon-bengal-rosette" in result

    def test_all_default_icons(self, parser):
        """Test all default Bengal icons render."""
        icons = ["terminal", "docs", "bengal-rosette"]
        for icon_name in icons:
            markdown = f""":::{{icon}} {icon_name}
:::"""
            result = parser.parse(markdown, {})
            assert "<svg" in result, f"Icon {icon_name} should render as SVG"
            assert f"icon-{icon_name}" in result


class TestIconDirectiveEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_icon(self, parser):
        """Test non-existent icon shows missing indicator."""
        markdown = """:::{icon} nonexistent-icon
:::"""
        result = parser.parse(markdown, {})
        # Should show missing icon indicator
        assert "bengal-icon-missing" in result or "❓" in result

    def test_empty_icon_name(self, parser):
        """Test empty icon name shows error."""
        markdown = """:::{icon}
:::"""
        result = parser.parse(markdown, {})
        # Should show error indicator
        assert "bengal-icon-error" in result or "⚠️" in result

    def test_invalid_size(self, parser):
        """Test invalid size falls back to default."""
        markdown = """:::{icon} terminal
:size: invalid
:::"""
        result = parser.parse(markdown, {})
        # Should fall back to default size 24
        assert 'width="24"' in result
        assert 'height="24"' in result

    def test_special_chars_in_aria_label(self, parser):
        """Test special characters in aria-label are escaped."""
        markdown = """:::{icon} terminal
:aria-label: <script>alert('xss')</script>
:::"""
        result = parser.parse(markdown, {})
        # Should be escaped
        assert "&lt;script&gt;" in result
        assert "<script>" not in result or "aria-label=" in result

    def test_multiple_icons(self, parser):
        """Test multiple icons in one document."""
        markdown = """:::{icon} terminal
:::

:::{icon} docs
:::

:::{icon} bengal-rosette
:::"""
        result = parser.parse(markdown, {})
        # Should have 3 SVGs
        assert result.count("<svg") == 3
        assert "icon-terminal" in result
        assert "icon-docs" in result
        assert "icon-bengal-rosette" in result


class TestIconDirectiveIntegration:
    """Test icon directive integration with other features."""

    def test_icon_in_admonition(self, parser):
        """Test icon inside admonition."""
        markdown = textwrap.dedent("""
        :::{note}
        This is a note with an icon: :::{icon} terminal
        :::
        :::
        """)
        result = parser.parse(markdown, {})
        assert "admonition" in result
        # Icon may or may not render in nested context
        # This tests that it doesn't break parsing

    def test_icon_with_heading(self, parser):
        """Test icon near heading."""
        markdown = textwrap.dedent("""
        ## Terminal

        :::{icon} terminal
        :size: 48
        :::

        Use the terminal for commands.
        """)
        result = parser.parse(markdown, {})
        assert "<h2>" in result
        assert "<svg" in result

    def test_icon_in_paragraph(self, parser):
        """Test icon as block (not inline in paragraph)."""
        markdown = textwrap.dedent("""
        Here is some text.

        :::{icon} terminal
        :::

        More text after.
        """)
        result = parser.parse(markdown, {})
        assert "<svg" in result


class TestIconDirectiveAliases:
    """Test directive aliases."""

    def test_svg_icon_alias(self, parser):
        """Test svg-icon alias works."""
        markdown = """:::{svg-icon} terminal
:::"""
        result = parser.parse(markdown, {})
        assert "<svg" in result
        assert "bengal-icon" in result


class TestGetAvailableIcons:
    """Test icon discovery functionality."""

    def test_get_available_icons(self):
        """Test get_available_icons returns icon names."""
        from bengal.rendering.plugins.directives.icon import get_available_icons

        icons = get_available_icons()
        assert isinstance(icons, list)
        # Should include our default icons
        assert "terminal" in icons
        assert "docs" in icons
        assert "bengal-rosette" in icons

    def test_icon_cache(self):
        """Test icon caching works."""
        from bengal.rendering.plugins.directives.icon import _icon_cache, _load_icon

        # Clear cache
        _icon_cache.clear()

        # Load icon twice
        result1 = _load_icon("terminal")
        result2 = _load_icon("terminal")

        # Should be cached
        assert result1 == result2
        assert "terminal" in _icon_cache
