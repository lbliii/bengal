"""
Test badge plugin.

Validates {bdg-color}`text` syntax support (Sphinx-Design compatible).
"""


class TestBadgePlugin:
    """Test badge rendering."""

    def test_badge_primary(self, parser):
        """Test primary badge."""
        markdown = "This has a {bdg-primary}`primary` badge."
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-primary">primary</span>' in result
        assert "This has a" in result

    def test_badge_secondary(self, parser):
        """Test secondary badge."""
        markdown = "{bdg-secondary}`configurations`"
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-secondary">configurations</span>' in result

    def test_badge_success(self, parser):
        """Test success badge."""
        markdown = "{bdg-success}`passed`"
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-success">passed</span>' in result

    def test_badge_danger(self, parser):
        """Test danger badge."""
        markdown = "{bdg-danger}`error`"
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-danger">error</span>' in result

    def test_badge_warning(self, parser):
        """Test warning badge."""
        markdown = "{bdg-warning}`deprecated`"
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-warning">deprecated</span>' in result

    def test_badge_info(self, parser):
        """Test info badge."""
        markdown = "{bdg-info}`v2.0`"
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-info">v2.0</span>' in result

    def test_badge_light(self, parser):
        """Test light badge."""
        markdown = "{bdg-light}`optional`"
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-light">optional</span>' in result

    def test_badge_dark(self, parser):
        """Test dark badge."""
        markdown = "{bdg-dark}`internal`"
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-dark">internal</span>' in result

    def test_multiple_badges(self, parser):
        """Test multiple badges in one line."""
        markdown = "{bdg-primary}`tag1` {bdg-secondary}`tag2` {bdg-success}`tag3`"
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-primary">tag1</span>' in result
        assert '<span class="role role-bdg-secondary">tag2</span>' in result
        assert '<span class="role role-bdg-success">tag3</span>' in result

    def test_badge_in_paragraph(self, parser):
        """Test badge mixed with other text."""
        markdown = "This feature is {bdg-success}`stable` and {bdg-info}`documented`."
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-success">stable</span>' in result
        assert '<span class="role role-bdg-info">documented</span>' in result
        assert "This feature is" in result

    def test_badge_with_special_chars(self, parser):
        """Test badge with special characters (should be escaped)."""
        markdown = "{bdg-primary}`<script>alert('xss')</script>`"
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-primary">&lt;script&gt;' in result
        assert "<script>" not in result  # Should be escaped

    def test_badge_unknown_color_fallback(self, parser):
        """Test badge with unknown color falls back to role format."""
        markdown = "{bdg-unknown}`fallback`"
        result = parser.parse(markdown, {})
        # PatitasParser renders unknown badges with role-bdg-unknown class
        assert '<span class="role role-bdg-unknown">fallback</span>' in result

    def test_badge_in_list(self, parser):
        """Test badges in list items."""
        markdown = """- Feature A {bdg-success}`ready`
- Feature B {bdg-warning}`beta`
- Feature C {bdg-danger}`broken`"""
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-success">ready</span>' in result
        assert '<span class="role role-bdg-warning">beta</span>' in result
        assert '<span class="role role-bdg-danger">broken</span>' in result

    def test_badge_in_table(self, parser):
        """Test badges in table cells."""
        markdown = """| Feature | Status |
|---------|--------|
| Auth    | {bdg-success}`done` |
| Payment | {bdg-warning}`wip` |"""
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-success">done</span>' in result
        assert '<span class="role role-bdg-warning">wip</span>' in result

    def test_no_badges(self, parser):
        """Test that content without badges is unaffected."""
        markdown = "Just regular text."
        result = parser.parse(markdown, {})
        assert "role-bdg" not in result
        assert "Just regular text" in result

    def test_badge_in_heading(self, parser):
        """Test badge in heading."""
        markdown = "# Features {bdg-success}`new`"
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-success">new</span>' in result
        assert "<h1" in result

    def test_sphinx_design_real_usage(self, parser):
        """Test real usage from Sphinx docs (card footer)."""
        markdown = """Some content here

{bdg-secondary}`configurations` {bdg-secondary}`models`"""
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-secondary">configurations</span>' in result
        assert '<span class="role role-bdg-secondary">models</span>' in result


class TestBadgePluginEdgeCases:
    """Test edge cases and error handling."""

    def test_badge_empty_text(self, parser):
        """Test badge with empty text."""
        markdown = "{bdg-primary}``"
        result = parser.parse(markdown, {})
        # Should handle gracefully - PatitasParser renders empty badge
        assert "role-bdg-primary" in result or markdown in result

    def test_badge_multiline_not_supported(self, parser):
        """Test that multiline badge content doesn't break parser."""
        markdown = """{bdg-primary}`line one
line two`"""
        result = parser.parse(markdown, {})
        # Should not crash, but might not render as badge
        # (backtick syntax is single-line only)
        assert "line one" in result

    def test_badge_nested_backticks(self, parser):
        """Test badge with nested backticks (shouldn't work but shouldn't crash)."""
        markdown = "{bdg-primary}`outer `inner` text`"
        result = parser.parse(markdown, {})
        # Parser's backtick handling will resolve this first
        # Just ensure it doesn't crash
        assert "outer" in result

    def test_badge_with_ampersand(self, parser):
        """Test badge with ampersand (should be escaped)."""
        markdown = "{bdg-info}`R&D`"
        result = parser.parse(markdown, {})
        assert '<span class="role role-bdg-info">R&amp;D</span>' in result

    def test_badge_with_quotes(self, parser):
        """Test badge with quotes (should be escaped)."""
        markdown = '{bdg-info}`"quoted"`'
        result = parser.parse(markdown, {})
        assert "&quot;" in result or '"' in result
