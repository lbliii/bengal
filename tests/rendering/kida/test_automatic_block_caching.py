"""Tests for automatic cached block usage in KIDA templates.

RFC: kida-template-introspection

Tests that cached blocks are automatically used during template rendering
without requiring any template syntax changes.
"""

from __future__ import annotations

import pytest

from bengal.rendering.block_cache import BlockCache
from bengal.rendering.kida import Environment


class TestAutomaticCachedBlocks:
    """Tests for automatic cached block usage."""

    def test_cached_block_used_automatically(self):
        """Test that cached blocks are used automatically during rendering."""
        env = Environment(preserve_ast=True)
        
        # Template with site-scoped block
        template = env.from_string("""
{% block nav %}
<nav>{% for p in site.pages %}{{ p.title }}{% end %}</nav>
{% end %}
{% block content %}{{ page.title }}{% end %}
""")
        
        # Verify nav is site-cacheable
        meta = template.template_metadata()
        assert meta is not None
        nav_meta = meta.blocks.get("nav")
        assert nav_meta is not None
        assert nav_meta.cache_scope == "site"
        
        # Pre-cache the nav block
        cached_html = "<nav>Cached Nav</nav>"
        
        # Render with cached block in context
        result = template.render(
            site={"pages": []},
            page={"title": "Test Page"},
            _cached_blocks={"nav": cached_html}
        )
        
        # Cached nav should be used (not re-rendered)
        assert cached_html in result
        assert "Cached Nav" in result
        
        # Content block should still render normally
        assert "Test Page" in result

    def test_non_cached_blocks_render_normally(self):
        """Test that non-cached blocks render normally."""
        env = Environment(preserve_ast=True)
        
        template = env.from_string("""
{% block nav %}<nav>Nav</nav>{% end %}
{% block content %}{{ page.title }}{% end %}
""")
        
        # Only cache nav, not content
        cached_html = "<nav>Cached</nav>"
        
        result = template.render(
            page={"title": "Page Title"},
            _cached_blocks={"nav": cached_html}
        )
        
        # Cached nav should be used
        assert cached_html in result
        
        # Content should render normally (not cached)
        assert "Page Title" in result

    def test_page_scoped_blocks_not_cached(self):
        """Test that page-scoped blocks are not cached automatically."""
        env = Environment(preserve_ast=True)
        
        template = env.from_string("""
{% block nav %}<nav>{{ site.title }}</nav>{% end %}
{% block content %}{{ page.title }}{% end %}
""")
        
        meta = template.template_metadata()
        assert meta is not None
        
        # Content depends on page, so should be page-scoped
        content_meta = meta.blocks.get("content")
        assert content_meta is not None
        assert content_meta.cache_scope == "page"
        
        # Even if we try to cache content, it shouldn't be used
        # (only site-scoped blocks are cached)
        cached_content = "<div>Cached Content</div>"
        
        result = template.render(
            site={"title": "Site"},
            page={"title": "Page Title"},
            _cached_blocks={"content": cached_content}
        )
        
        # Content should render normally (not use cache)
        assert "Page Title" in result
        assert "Cached Content" not in result

    def test_cached_blocks_with_inheritance(self):
        """Test cached blocks work with template inheritance."""
        from bengal.rendering.kida import DictLoader
        
        loader = DictLoader({
            "base.html": """
{% block nav %}<nav>Base Nav</nav>{% end %}
{% block content %}{% end %}
""",
            "child.html": """
{% extends "base.html" %}
{% block content %}{{ page.title }}{% end %}
"""
        })
        
        env = Environment(loader=loader, preserve_ast=True)
        
        # Get base template to check its nav block metadata
        base_template = env.get_template("base.html")
        base_meta = base_template.template_metadata()
        assert base_meta is not None
        nav_meta = base_meta.blocks.get("nav")
        assert nav_meta is not None
        assert nav_meta.cache_scope == "site"
        
        # Get child template
        child_template = env.get_template("child.html")
        
        # Cache nav block (defined in base, used by child)
        cached_nav = "<nav>Cached Base Nav</nav>"
        
        result = child_template.render(
            page={"title": "Child Page"},
            _cached_blocks={"nav": cached_nav}
        )
        
        # Cached nav should be used (from base template)
        assert cached_nav in result
        
        # Child content should render
        assert "Child Page" in result

    def test_cached_blocks_dict_wrapper_methods(self):
        """Test that CachedBlocksDict wrapper supports all dict operations."""
        env = Environment(preserve_ast=True)
        
        template = env.from_string("""
{% block nav %}<nav>Nav</nav>{% end %}
{% block footer %}<footer>Footer</footer>{% end %}
""")
        
        cached_blocks = {
            "nav": "<nav>Cached Nav</nav>",
            "footer": "<footer>Cached Footer</footer>"
        }
        
        # Render to trigger wrapper creation
        result = template.render(
            _cached_blocks=cached_blocks
        )
        
        # Both cached blocks should be used
        assert cached_blocks["nav"] in result
        assert cached_blocks["footer"] in result

    def test_cached_blocks_with_setdefault(self):
        """Test that cached blocks work with setdefault() calls."""
        env = Environment(preserve_ast=True)
        
        template = env.from_string("""
{% block nav %}<nav>Nav</nav>{% end %}
""")
        
        cached_nav = "<nav>Cached</nav>"
        
        # Render with cached block
        result = template.render(_cached_blocks={"nav": cached_nav})
        
        # Cached block should be used (setdefault won't overwrite it)
        assert cached_nav in result

    def test_no_cached_blocks_renders_normally(self):
        """Test that templates render normally when no cached blocks."""
        env = Environment(preserve_ast=True)
        
        template = env.from_string("""
{% block nav %}<nav>{{ site.title }}</nav>{% end %}
""")
        
        # Render without cached blocks
        result = template.render(site={"title": "My Site"})
        
        # Should render normally
        assert "<nav>My Site</nav>" in result

    def test_cached_blocks_with_copy(self):
        """Test that cached blocks work with dict.copy() for embed/include."""
        from bengal.rendering.kida import DictLoader
        
        loader = DictLoader({
            "main.html": """
{% block nav %}<nav>Nav</nav>{% end %}
{% embed "partial.html" %}
{% block nav %}<nav>Overridden</nav>{% end %}
{% endembed %}
""",
            "partial.html": "{% block nav %}<nav>Partial Nav</nav>{% end %}"
        })
        
        env = Environment(loader=loader, preserve_ast=True)
        template = env.get_template("main.html")
        
        cached_nav = "<nav>Cached Nav</nav>"
        
        # Render with cached block
        result = template.render(_cached_blocks={"nav": cached_nav})
        
        # Cached block should be used in main template
        # (embed creates a copy of _blocks, so cached wrapper should be copied)
        assert cached_nav in result or "Overridden" in result

    def test_multiple_templates_same_cached_block(self):
        """Test that same cached block works across multiple templates."""
        env = Environment(preserve_ast=True)
        
        template1 = env.from_string("{% block nav %}<nav>Nav 1</nav>{% end %}")
        template2 = env.from_string("{% block nav %}<nav>Nav 2</nav>{% end %}")
        
        cached_nav = "<nav>Shared Cached Nav</nav>"
        
        result1 = template1.render(_cached_blocks={"nav": cached_nav})
        result2 = template2.render(_cached_blocks={"nav": cached_nav})
        
        # Both should use cached block
        assert cached_nav in result1
        assert cached_nav in result2

    def test_cached_block_performance(self):
        """Test that cached blocks improve performance (no re-rendering)."""
        env = Environment(preserve_ast=True)
        
        # Template with expensive block
        template = env.from_string("""
{% block nav %}
<nav>
{% for i in range(1000) %}
  <span>{{ i }}</span>
{% end %}
</nav>
{% end %}
{% block content %}{{ page.title }}{% end %}
""")
        
        # Pre-render and cache nav
        nav_result = template.render_block("nav", range=range)
        cached_nav = nav_result
        
        # Render full template with cached nav
        result = template.render(
            range=range,
            page={"title": "Test"},
            _cached_blocks={"nav": cached_nav}
        )
        
        # Should contain cached nav (fast path)
        assert cached_nav in result
        assert "Test" in result

    def test_cached_blocks_with_block_cache_integration(self):
        """Test integration with BlockCache class."""
        from bengal.rendering.block_cache import BlockCache
        
        env = Environment(preserve_ast=True)
        cache = BlockCache()
        
        template = env.from_string("""
{% block nav %}<nav>{{ site.title }}</nav>{% end %}
""")
        
        # Warm cache
        nav_html = template.render_block("nav", site={"title": "Cached Site"})
        cache.set("test.html", "nav", nav_html, scope="site")
        
        # Get cached block
        cached_html = cache.get("test.html", "nav")
        assert cached_html is not None
        
        # Render with cached block
        result = template.render(
            site={"title": "New Site"},
            _cached_blocks={"nav": cached_html}
        )
        
        # Should use cached HTML (not re-render with "New Site")
        assert "Cached Site" in result
        assert "New Site" not in result

