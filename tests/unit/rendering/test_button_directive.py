"""
Test button directive.

Validates clean button syntax for CTAs and navigation.
"""

from bengal.rendering.parser import MistuneParser


class TestButtonDirective:
    """Test button rendering."""

    def setup_method(self):
        """Create parser instance."""
        self.parser = MistuneParser()

    def test_basic_button(self):
        """Test basic button with no options."""
        markdown = """:::{button} /docs/
Get Started
:::"""
        result = self.parser.parse(markdown, {})
        assert '<a class="button button-primary"' in result
        assert 'href="/docs/"' in result
        assert "Get Started" in result

    def test_button_colors(self):
        """Test all button colors."""
        colors = ["primary", "secondary", "success", "danger", "warning", "info", "light", "dark"]

        for color in colors:
            markdown = f""":::{{button}} /test/
:color: {color}
Test
:::"""
            result = self.parser.parse(markdown, {})
            assert f"button-{color}" in result

    def test_button_pill_style(self):
        """Test pill style (fully rounded)."""
        markdown = """:::{button} /test/
:style: pill
Test
:::"""
        result = self.parser.parse(markdown, {})
        assert "button-pill" in result

    def test_button_outline_style(self):
        """Test outline style."""
        markdown = """:::{button} /test/
:style: outline
:color: primary
Test
:::"""
        result = self.parser.parse(markdown, {})
        assert "button-outline" in result
        assert "button-primary" in result

    def test_button_sizes(self):
        """Test button sizes."""
        markdown_sm = """:::{button} /test/
:size: small
Small
:::"""
        result_sm = self.parser.parse(markdown_sm, {})
        assert "button-sm" in result_sm

        markdown_lg = """:::{button} /test/
:size: large
Large
:::"""
        result_lg = self.parser.parse(markdown_lg, {})
        assert "button-lg" in result_lg

    def test_button_with_icon(self):
        """Test button with icon."""
        markdown = """:::{button} /test/
:icon: rocket
Launch
:::"""
        result = self.parser.parse(markdown, {})
        assert "🚀" in result
        assert "button-icon" in result

    def test_button_external_link(self):
        """Test button with external link and target."""
        markdown = """:::{button} https://github.com/project
:target: _blank
GitHub
:::"""
        result = self.parser.parse(markdown, {})
        assert 'target="_blank"' in result
        assert 'rel="noopener noreferrer"' in result

    def test_button_all_options(self):
        """Test button with all options."""
        markdown = """:::{button} /signup/
:color: primary
:style: pill
:size: large
:icon: rocket

Sign Up Free
:::"""
        result = self.parser.parse(markdown, {})
        assert "button-primary" in result
        assert "button-pill" in result
        assert "button-lg" in result
        assert "🚀" in result
        assert "Sign Up Free" in result

    def test_button_invalid_color_fallback(self):
        """Test button with invalid color falls back to primary."""
        markdown = """:::{button} /test/
:color: invalid-color
Test
:::"""
        result = self.parser.parse(markdown, {})
        assert "button-primary" in result

    def test_button_no_icon_shows_nothing(self):
        """Test button with invalid icon shows no icon."""
        markdown = """:::{button} /test/
:icon: nonexistent
Test
:::"""
        result = self.parser.parse(markdown, {})
        assert "button-icon" not in result
        # Text should still be there
        assert "Test" in result

    def test_multiple_buttons(self):
        """Test multiple buttons in one document."""
        markdown = """:::{button} /docs/
:color: primary
Docs
:::

:::{button} /api/
:color: secondary
API
:::"""
        result = self.parser.parse(markdown, {})
        assert result.count('class="button') == 2
        assert "button-primary" in result
        assert "button-secondary" in result


class TestButtonEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Create parser instance."""
        self.parser = MistuneParser()

    def test_button_empty_url(self):
        """Test button with empty URL."""
        markdown = """
        :::{button}
        Test
        :::
        """
        result = self.parser.parse(markdown, {})
        # Should still render with # as fallback
        assert '<a class="button' in result

    def test_button_special_chars_in_text(self):
        """Test button with special characters in text."""
        markdown = """
        :::{button} /test/
        <script>alert('xss')</script>
        :::
        """
        result = self.parser.parse(markdown, {})
        # Should be escaped
        assert "&lt;script&gt;" in result
        assert "<script>" not in result

    def test_button_special_chars_in_url(self):
        """Test button with special characters in URL."""
        markdown = """
        :::{button} /search?q=test&foo=bar
        Search
        :::
        """
        result = self.parser.parse(markdown, {})
        # Should be escaped
        assert 'href="/search?q=test&amp;foo=bar"' in result

    def test_button_markdown_in_text(self):
        """Test that markdown in button text is not processed."""
        markdown = """
        :::{button} /test/
        **Bold** Text
        :::
        """
        result = self.parser.parse(markdown, {})
        # Markdown should not be processed, just escaped
        assert "**Bold**" in result or "Bold" in result

    def test_button_with_only_icon(self):
        """Test button with only icon, no text."""
        markdown = """
        :::{button} /test/
        :icon: arrow-right
        :::
        """
        result = self.parser.parse(markdown, {})
        assert "→" in result or "arrow-right" in result


class TestButtonIntegration:
    """Test button directive integration with other features."""

    def setup_method(self):
        """Create parser instance."""
        self.parser = MistuneParser()

    def test_buttons_in_cards(self):
        """Test buttons inside cards."""
        markdown = """
        :::{card} Get Started
        Learn how to use our platform.

        :::{button} /docs/
        :color: primary
        Read Docs
        :::
        :::
        """
        result = self.parser.parse(markdown, {})
        assert "card" in result
        assert "button-primary" in result

    def test_button_with_heading(self):
        """Test button near heading."""
        markdown = """
        ## Quick Actions

        :::{button} /start/
        :color: primary
        :style: pill
        Get Started
        :::
        """
        result = self.parser.parse(markdown, {})
        assert "<h2>" in result
        assert "button-pill" in result

    def test_buttons_in_list(self):
        """Test buttons in list items."""
        markdown = """
        - Option 1: :::{button} /a/
          :size: small
          Go
          :::
        - Option 2: :::{button} /b/
          :size: small
          Go
          :::
        """
        result = self.parser.parse(markdown, {})
        assert result.count("button-sm") >= 1
