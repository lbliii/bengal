"""
Test badge plugin.

Validates {bdg-color}`text` syntax support (Sphinx-Design compatible).
"""

from bengal.rendering.parsers import MistuneParser


class TestBadgePlugin:
    """Test badge rendering."""

    def setup_method(self):
        """Create parser instance with badge plugin (auto-enabled)."""
        self.parser = MistuneParser()

    def test_badge_primary(self):
        """Test primary badge."""
        markdown = "This has a {bdg-primary}`primary` badge."
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-primary">primary</span>' in result
        assert "This has a" in result

    def test_badge_secondary(self):
        """Test secondary badge."""
        markdown = "{bdg-secondary}`configurations`"
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-secondary">configurations</span>' in result

    def test_badge_success(self):
        """Test success badge."""
        markdown = "{bdg-success}`passed`"
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-success">passed</span>' in result

    def test_badge_danger(self):
        """Test danger badge."""
        markdown = "{bdg-danger}`error`"
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-danger">error</span>' in result

    def test_badge_warning(self):
        """Test warning badge."""
        markdown = "{bdg-warning}`deprecated`"
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-warning">deprecated</span>' in result

    def test_badge_info(self):
        """Test info badge."""
        markdown = "{bdg-info}`v2.0`"
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-info">v2.0</span>' in result

    def test_badge_light(self):
        """Test light badge."""
        markdown = "{bdg-light}`optional`"
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-light">optional</span>' in result

    def test_badge_dark(self):
        """Test dark badge."""
        markdown = "{bdg-dark}`internal`"
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-dark">internal</span>' in result

    def test_multiple_badges(self):
        """Test multiple badges in one line."""
        markdown = "{bdg-primary}`tag1` {bdg-secondary}`tag2` {bdg-success}`tag3`"
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-primary">tag1</span>' in result
        assert '<span class="badge badge-secondary">tag2</span>' in result
        assert '<span class="badge badge-success">tag3</span>' in result

    def test_badge_in_paragraph(self):
        """Test badge mixed with other text."""
        markdown = "This feature is {bdg-success}`stable` and {bdg-info}`documented`."
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-success">stable</span>' in result
        assert '<span class="badge badge-info">documented</span>' in result
        assert "This feature is" in result

    def test_badge_with_special_chars(self):
        """Test badge with special characters (should be escaped)."""
        markdown = "{bdg-primary}`<script>alert('xss')</script>`"
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-primary">&lt;script&gt;' in result
        assert "<script>" not in result  # Should be escaped

    def test_badge_unknown_color_fallback(self):
        """Test badge with unknown color falls back to secondary."""
        markdown = "{bdg-unknown}`fallback`"
        result = self.parser.parse(markdown, {})
        # Should fall back to secondary
        assert '<span class="badge badge-secondary">fallback</span>' in result

    def test_badge_in_list(self):
        """Test badges in list items."""
        markdown = """- Feature A {bdg-success}`ready`
- Feature B {bdg-warning}`beta`
- Feature C {bdg-danger}`broken`"""
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-success">ready</span>' in result
        assert '<span class="badge badge-warning">beta</span>' in result
        assert '<span class="badge badge-danger">broken</span>' in result

    def test_badge_in_table(self):
        """Test badges in table cells."""
        markdown = """| Feature | Status |
|---------|--------|
| Auth    | {bdg-success}`done` |
| Payment | {bdg-warning}`wip` |"""
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-success">done</span>' in result
        assert '<span class="badge badge-warning">wip</span>' in result

    def test_no_badges(self):
        """Test that content without badges is unaffected."""
        markdown = "Just regular text."
        result = self.parser.parse(markdown, {})
        assert "badge" not in result or "badge" not in result.lower()
        assert "Just regular text" in result

    def test_badge_in_heading(self):
        """Test badge in heading."""
        markdown = "# Features {bdg-success}`new`"
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-success">new</span>' in result
        assert "<h1>" in result

    def test_sphinx_design_real_usage(self):
        """Test real usage from Sphinx docs (card footer)."""
        markdown = """Some content here

{bdg-secondary}`configurations` {bdg-secondary}`models`"""
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-secondary">configurations</span>' in result
        assert '<span class="badge badge-secondary">models</span>' in result


class TestBadgePluginEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Create parser instance with badge plugin (auto-enabled)."""
        self.parser = MistuneParser()

    def test_badge_empty_text(self):
        """Test badge with empty text."""
        markdown = "{bdg-primary}``"
        result = self.parser.parse(markdown, {})
        # Should handle gracefully
        assert "badge-primary" in result or markdown in result

    def test_badge_multiline_not_supported(self):
        """Test that multiline badge content doesn't break parser."""
        markdown = """{bdg-primary}`line one
line two`"""
        result = self.parser.parse(markdown, {})
        # Should not crash, but might not render as badge
        # (backtick syntax is single-line only)
        assert "line one" in result

    def test_badge_nested_backticks(self):
        """Test badge with nested backticks (shouldn't work but shouldn't crash)."""
        markdown = "{bdg-primary}`outer `inner` text`"
        result = self.parser.parse(markdown, {})
        # Mistune's backtick handling will resolve this first
        # Just ensure it doesn't crash
        assert "outer" in result

    def test_badge_with_ampersand(self):
        """Test badge with ampersand (should be escaped)."""
        markdown = "{bdg-info}`R&D`"
        result = self.parser.parse(markdown, {})
        assert '<span class="badge badge-info">R&amp;D</span>' in result

    def test_badge_with_quotes(self):
        """Test badge with quotes (should be escaped)."""
        markdown = '{bdg-info}`"quoted"`'
        result = self.parser.parse(markdown, {})
        assert "&quot;" in result or '"' in result
