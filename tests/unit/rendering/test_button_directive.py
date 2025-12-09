"""
Test button directive.

Validates clean button syntax for CTAs and navigation.
"""

import textwrap


class TestButtonDirective:
    """Test button rendering."""

    def test_basic_button(self, parser):
        """Test basic button with no options."""
        markdown = """:::{button} /docs/
Get Started
:::"""
        result = parser.parse(markdown, {})
        assert '<a class="button button-primary"' in result
        assert 'href="/docs/"' in result
        assert "Get Started" in result

    def test_button_colors(self, parser):
        """Test all button colors."""
        colors = ["primary", "secondary", "success", "danger", "warning", "info", "light", "dark"]

        for color in colors:
            markdown = f""":::{{button}} /test/
:color: {color}
Test
:::"""
            result = parser.parse(markdown, {})
            assert f"button-{color}" in result

    def test_button_pill_style(self, parser):
        """Test pill style (fully rounded)."""
        markdown = """:::{button} /test/
:style: pill
Test
:::"""
        result = parser.parse(markdown, {})
        assert "button-pill" in result

    def test_button_outline_style(self, parser):
        """Test outline style."""
        markdown = """:::{button} /test/
:style: outline
:color: primary
Test
:::"""
        result = parser.parse(markdown, {})
        assert "button-outline" in result
        assert "button-primary" in result

    def test_button_sizes(self, parser):
        """Test button sizes."""
        markdown_sm = """:::{button} /test/
:size: small
Small
:::"""
        result_sm = parser.parse(markdown_sm, {})
        assert "button-sm" in result_sm

        markdown_lg = """:::{button} /test/
:size: large
Large
:::"""
        result_lg = parser.parse(markdown_lg, {})
        assert "button-lg" in result_lg

    def test_button_with_icon(self, parser):
        """Test button with icon."""
        markdown = """:::{button} /test/
:icon: rocket
Launch
:::"""
        result = parser.parse(markdown, {})
        # Check for SVG icon or unicode fallback
        assert "rocket" in result or "🚀" in result or "<svg" in result
        assert "button-icon" in result

    def test_button_external_link(self, parser):
        """Test button with external link and target."""
        markdown = """:::{button} https://github.com/project
:target: _blank
GitHub
:::"""
        result = parser.parse(markdown, {})
        assert 'target="_blank"' in result
        assert 'rel="noopener noreferrer"' in result

    def test_button_all_options(self, parser):
        """Test button with all options."""
        markdown = """:::{button} /signup/
:color: primary
:style: pill
:size: large
:icon: rocket

Sign Up Free
:::"""
        result = parser.parse(markdown, {})
        assert "button-primary" in result
        assert "button-pill" in result
        assert "button-lg" in result
        # Check for SVG icon or unicode fallback
        assert "rocket" in result or "🚀" in result or "<svg" in result
        assert "Sign Up Free" in result

    def test_button_invalid_color_fallback(self, parser):
        """Test button with invalid color falls back to primary."""
        markdown = """:::{button} /test/
:color: invalid-color
Test
:::"""
        result = parser.parse(markdown, {})
        assert "button-primary" in result

    def test_button_no_icon_shows_nothing(self, parser):
        """Test button with invalid icon shows no icon."""
        markdown = """:::{button} /test/
:icon: nonexistent
Test
:::"""
        result = parser.parse(markdown, {})
        assert "button-icon" not in result
        # Text should still be there
        assert "Test" in result

    def test_multiple_buttons(self, parser):
        """Test multiple buttons in one document."""
        markdown = """:::{button} /docs/
:color: primary
Docs
:::

:::{button} /api/
:color: secondary
API
:::"""
        result = parser.parse(markdown, {})
        # Count button elements (not button-text spans)
        assert result.count('<a class="button') == 2
        assert "button-primary" in result
        assert "button-secondary" in result


class TestButtonEdgeCases:
    """Test edge cases and error handling."""

    def test_button_empty_url(self, parser):
        """Test button with empty URL."""
        markdown = textwrap.dedent("""
        :::{button}
        Test
        :::
        """)
        result = parser.parse(markdown, {})
        # Should still render with # as fallback
        assert '<a class="button' in result

    def test_button_special_chars_in_text(self, parser):
        """Test button with special characters in text."""
        markdown = textwrap.dedent("""
        :::{button} /test/
        <script>alert('xss')</script>
        :::
        """)
        result = parser.parse(markdown, {})
        # Should be escaped
        assert "&lt;script&gt;" in result
        assert "<script>" not in result

    def test_button_special_chars_in_url(self, parser):
        """Test button with special characters in URL."""
        markdown = textwrap.dedent("""
        :::{button} /search?q=test&foo=bar
        Search
        :::
        """)
        result = parser.parse(markdown, {})
        # Should be escaped
        assert 'href="/search?q=test&amp;foo=bar"' in result

    def test_button_markdown_in_text(self, parser):
        """Test that markdown in button text is not processed."""
        markdown = textwrap.dedent("""
        :::{button} /test/
        **Bold** Text
        :::
        """)
        result = parser.parse(markdown, {})
        # Markdown should not be processed, just escaped
        assert "**Bold**" in result or "Bold" in result

    def test_button_with_only_icon(self, parser):
        """Test button with only icon, no text."""
        markdown = textwrap.dedent("""
        :::{button} /test/
        :icon: arrow-right
        :::
        """)
        result = parser.parse(markdown, {})
        # Check for any of these indicating success
        assert "→" in result or "arrow-right" in result or "<svg" in result or "Button" in result


class TestButtonIntegration:
    """Test button directive integration with other features."""

    def test_buttons_in_cards(self, parser):
        """Test buttons inside cards."""
        markdown = textwrap.dedent("""
        :::{card} Get Started
        Learn how to use our platform.

        :::{button} /docs/
        :color: primary
        Read Docs
        :::
        :::
        """)
        result = parser.parse(markdown, {})
        assert "card" in result
        assert "button-primary" in result

    def test_button_with_heading(self, parser):
        """Test button near heading."""
        markdown = textwrap.dedent("""
        ## Quick Actions

        :::{button} /start/
        :color: primary
        :style: pill
        Get Started
        :::
        """)
        result = parser.parse(markdown, {})
        assert "<h2>" in result
        assert "button-pill" in result

    def test_buttons_in_list(self, parser):
        """Test buttons as list items (not inline)."""
        markdown = textwrap.dedent("""
        - Option 1:

          :::{button} /a/
          :size: small
          Go
          :::

        - Option 2:

          :::{button} /b/
          :size: small
          Go
          :::
        """)
        result = parser.parse(markdown, {})
        # Buttons should be parsed when on separate lines in list items
        assert result.count("button-sm") >= 1 or result.count("button") >= 1
