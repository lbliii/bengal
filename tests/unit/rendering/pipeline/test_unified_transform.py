"""
Tests for the unified HTML transformer.

RFC: rfc-rendering-package-optimizations.md
"""

from __future__ import annotations

from bengal.rendering.pipeline.unified_transform import (
    HybridHTMLTransformer,
    create_transformer,
)


class TestHybridHTMLTransformer:
    """Tests for HybridHTMLTransformer class."""

    def test_empty_input_returns_empty(self):
        """Empty string should return empty string."""
        transformer = HybridHTMLTransformer()
        assert transformer.transform("") == ""

    def test_none_baseurl_skips_internal_transform(self):
        """No baseurl should skip internal link transformation."""
        transformer = HybridHTMLTransformer("")
        html = '<a href="/docs/">Docs</a>'
        result = transformer.transform(html)
        assert result == '<a href="/docs/">Docs</a>'

    def test_jinja_block_escaping(self):
        """Jinja blocks should be escaped to HTML entities."""
        transformer = HybridHTMLTransformer()
        html = "<pre>{% for item in items %}{{ item }}{% endfor %}</pre>"
        result = transformer.transform(html)
        assert "&#123;%" in result
        assert "%&#125;" in result
        # Variable syntax is NOT escaped by this transformer (only blocks)
        assert "{{ item }}" in result


class TestMarkdownLinkNormalization:
    """Tests for .md link normalization."""

    def test_simple_md_link(self):
        """Simple .md link should become clean URL."""
        transformer = HybridHTMLTransformer()
        html = '<a href="./guide.md">Guide</a>'
        result = transformer.transform(html)
        assert 'href="./guide/"' in result

    def test_index_md_becomes_parent(self):
        """_index.md should become parent directory."""
        transformer = HybridHTMLTransformer()
        html = '<a href="./_index.md">Index</a>'
        result = transformer.transform(html)
        assert 'href="./"' in result

    def test_path_index_md(self):
        """path/_index.md should become path/."""
        transformer = HybridHTMLTransformer()
        html = '<a href="../related/_index.md">Related</a>'
        result = transformer.transform(html)
        assert 'href="../related/"' in result

    def test_regular_index_md(self):
        """path/index.md should become path/."""
        transformer = HybridHTMLTransformer()
        html = '<a href="./section/index.md">Section</a>'
        result = transformer.transform(html)
        assert 'href="./section/"' in result

    def test_deep_path_md_link(self):
        """Deep path .md links should work."""
        transformer = HybridHTMLTransformer()
        html = '<a href="../advanced/feature-c.md">Feature C</a>'
        result = transformer.transform(html)
        assert 'href="../advanced/feature-c/"' in result

    def test_multiple_md_links(self):
        """Multiple .md links should all be transformed."""
        transformer = HybridHTMLTransformer()
        html = """
        <a href="./a.md">A</a>
        <a href="./b.md">B</a>
        <a href="../c.md">C</a>
        """
        result = transformer.transform(html)
        assert 'href="./a/"' in result
        assert 'href="./b/"' in result
        assert 'href="../c/"' in result


class TestInternalLinkTransformation:
    """Tests for baseurl prefixing."""

    def test_internal_link_prefixed(self):
        """Internal links should get baseurl prefix."""
        transformer = HybridHTMLTransformer("/bengal")
        html = '<a href="/docs/guide/">Guide</a>'
        result = transformer.transform(html)
        assert 'href="/bengal/docs/guide/"' in result

    def test_external_links_unchanged(self):
        """External links should not be modified."""
        transformer = HybridHTMLTransformer("/bengal")
        html = '<a href="https://external.com/">External</a>'
        result = transformer.transform(html)
        assert 'href="https://external.com/"' in result

    def test_anchor_links_unchanged(self):
        """Anchor links should not be modified."""
        transformer = HybridHTMLTransformer("/bengal")
        html = '<a href="#section">Section</a>'
        result = transformer.transform(html)
        assert 'href="#section"' in result

    def test_relative_links_unchanged(self):
        """Relative links (no leading /) should not be modified."""
        transformer = HybridHTMLTransformer("/bengal")
        html = '<a href="relative/path/">Relative</a>'
        result = transformer.transform(html)
        assert 'href="relative/path/"' in result

    def test_already_prefixed_unchanged(self):
        """Links already with baseurl should not be double-prefixed."""
        transformer = HybridHTMLTransformer("/bengal")
        html = '<a href="/bengal/docs/">Docs</a>'
        result = transformer.transform(html)
        assert 'href="/bengal/docs/"' in result
        assert "/bengal/bengal/" not in result

    def test_img_src_prefixed(self):
        """Image src attributes should also be prefixed."""
        transformer = HybridHTMLTransformer("/bengal")
        html = '<img src="/assets/logo.svg" alt="Logo">'
        result = transformer.transform(html)
        assert 'src="/bengal/assets/logo.svg"' in result

    def test_multiple_internal_links(self):
        """Multiple internal links should all be prefixed."""
        transformer = HybridHTMLTransformer("/bengal")
        html = """
        <a href="/docs/">Docs</a>
        <a href="/api/">API</a>
        <img src="/assets/image.png">
        """
        result = transformer.transform(html)
        assert 'href="/bengal/docs/"' in result
        assert 'href="/bengal/api/"' in result
        assert 'src="/bengal/assets/image.png"' in result


class TestCombinedTransformations:
    """Tests for combined .md and baseurl transformations."""

    def test_md_link_with_baseurl(self):
        """Should handle both .md normalization and baseurl in one pass."""
        transformer = HybridHTMLTransformer("/bengal")
        html = """
        <a href="./guide.md">Guide</a>
        <a href="/docs/">Docs</a>
        """
        result = transformer.transform(html)
        # .md should be normalized
        assert 'href="./guide/"' in result
        # Internal should be prefixed
        assert 'href="/bengal/docs/"' in result

    def test_all_transform_types(self):
        """Should handle all transformation types together."""
        transformer = HybridHTMLTransformer("/bengal")
        html = """
        <p>{% if production %}Prod{% endif %}</p>
        <a href="./intro.md">Intro</a>
        <a href="/api/reference/">API</a>
        <a href="https://external.com/">External</a>
        <img src="/assets/hero.png">
        """
        result = transformer.transform(html)

        # Jinja blocks escaped
        assert "&#123;%" in result
        assert "%&#125;" in result

        # .md normalized
        assert 'href="./intro/"' in result

        # Internal prefixed
        assert 'href="/bengal/api/reference/"' in result
        assert 'src="/bengal/assets/hero.png"' in result

        # External unchanged
        assert 'href="https://external.com/"' in result


class TestEdgeCases:
    """Edge case tests."""

    def test_no_transformable_content(self):
        """Content with nothing to transform should pass through unchanged."""
        transformer = HybridHTMLTransformer("/bengal")
        html = "<p>Simple paragraph with no links.</p>"
        result = transformer.transform(html)
        assert result == html

    def test_single_quotes(self):
        """Should handle single-quoted attributes."""
        transformer = HybridHTMLTransformer("/bengal")
        html = "<a href='./guide.md'>Guide</a>"
        result = transformer.transform(html)
        assert "href='./guide/'" in result

    def test_mixed_quotes(self):
        """Should handle mixed quote styles."""
        transformer = HybridHTMLTransformer("/bengal")
        html = """
        <a href="./a.md">A</a>
        <a href='./b.md'>B</a>
        """
        result = transformer.transform(html)
        assert 'href="./a/"' in result
        assert "href='./b/'" in result


class TestCreateTransformer:
    """Tests for the factory function."""

    def test_creates_with_baseurl(self):
        """Should create transformer with baseurl from config."""
        config = {"baseurl": "/mysite"}
        transformer = create_transformer(config)

        html = '<a href="/docs/">Docs</a>'
        result = transformer.transform(html)
        assert 'href="/mysite/docs/"' in result

    def test_creates_without_baseurl(self):
        """Should create transformer without baseurl when not in config."""
        config = {}
        transformer = create_transformer(config)

        html = '<a href="/docs/">Docs</a>'
        result = transformer.transform(html)
        assert 'href="/docs/"' in result

    def test_handles_none_baseurl(self):
        """Should handle None baseurl in config."""
        config = {"baseurl": None}
        transformer = create_transformer(config)

        html = '<a href="/docs/">Docs</a>'
        result = transformer.transform(html)
        assert 'href="/docs/"' in result

    def test_strips_trailing_slash(self):
        """Should strip trailing slash from baseurl."""
        config = {"baseurl": "/mysite/"}
        transformer = create_transformer(config)

        html = '<a href="/docs/">Docs</a>'
        result = transformer.transform(html)
        assert 'href="/mysite/docs/"' in result
        # Not /mysite//docs/
        assert "/mysite//docs/" not in result
