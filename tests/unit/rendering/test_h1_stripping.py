"""Tests for automatic H1 stripping in rendered content."""

from __future__ import annotations

from unittest.mock import Mock

from bengal.rendering.renderer import Renderer


class TestH1Stripping:
    """Test that the first H1 is automatically stripped from content."""

    def test_strips_first_h1(self):
        """Should remove the first H1 tag from content."""
        template_engine = Mock()
        template_engine.site = Mock()
        template_engine.site.config = {}
        renderer = Renderer(template_engine)

        content = "<h1>My Title</h1><p>Content here</p>"
        result = renderer._strip_first_h1(content)

        assert result == "<p>Content here</p>"

    def test_strips_first_h1_with_attributes(self):
        """Should remove H1 even with attributes like id or class."""
        template_engine = Mock()
        template_engine.site = Mock()
        template_engine.site.config = {}
        renderer = Renderer(template_engine)

        content = '<h1 id="title" class="main-title">My Title</h1><p>Content</p>'
        result = renderer._strip_first_h1(content)

        assert result == "<p>Content</p>"

    def test_keeps_subsequent_h1s(self):
        """Should only remove the first H1, keeping any later ones."""
        template_engine = Mock()
        template_engine.site = Mock()
        template_engine.site.config = {}
        renderer = Renderer(template_engine)

        content = """<h1>First Title</h1>
<p>Some content</p>
<h1>Second Title</h1>
<p>More content</p>"""

        result = renderer._strip_first_h1(content)

        assert "<h1>First Title</h1>" not in result
        assert "<h1>Second Title</h1>" in result
        assert "<p>Some content</p>" in result
        assert "<p>More content</p>" in result

    def test_handles_multiline_h1(self):
        """Should handle H1 content that spans multiple lines."""
        template_engine = Mock()
        template_engine.site = Mock()
        template_engine.site.config = {}
        renderer = Renderer(template_engine)

        content = """<h1>
    Multi-line
    Title
</h1><p>Content</p>"""

        result = renderer._strip_first_h1(content)

        assert "<h1>" not in result
        assert "</h1>" not in result
        assert "<p>Content</p>" in result

    def test_handles_no_h1(self):
        """Should return content unchanged if there's no H1."""
        template_engine = Mock()
        template_engine.site = Mock()
        template_engine.site.config = {}
        renderer = Renderer(template_engine)

        content = "<h2>Subtitle</h2><p>Content</p>"
        result = renderer._strip_first_h1(content)

        assert result == content

    def test_case_insensitive(self):
        """Should match H1 in any case (H1, h1, H1, etc)."""
        template_engine = Mock()
        template_engine.site = Mock()
        template_engine.site.config = {}
        renderer = Renderer(template_engine)

        # Uppercase
        content = "<H1>Title</H1><p>Content</p>"
        result = renderer._strip_first_h1(content)
        assert "<H1>" not in result
        assert "<p>Content</p>" in result

        # Mixed case
        content = "<H1>Title</h1><p>Content</p>"
        result = renderer._strip_first_h1(content)
        assert "<H1>" not in result
        assert "<p>Content</p>" in result

    def test_render_content_calls_strip(self):
        """render_content should automatically strip the first H1."""
        template_engine = Mock()
        template_engine.site = Mock()
        template_engine.site.config = {}
        renderer = Renderer(template_engine)

        content = "<h1>Title</h1><p>Content</p>"
        result = renderer.render_content(content)

        assert "<h1>" not in result
        assert "<p>Content</p>" in result

    def test_preserves_nested_content(self):
        """Should preserve complex nested content within H1."""
        template_engine = Mock()
        template_engine.site = Mock()
        template_engine.site.config = {}
        renderer = Renderer(template_engine)

        content = '<h1>Title <span class="badge">New</span></h1><p>Content</p>'
        result = renderer._strip_first_h1(content)

        assert "<h1>" not in result
        assert "</h1>" not in result
        assert "<p>Content</p>" in result
