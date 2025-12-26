"""Tests for Kida Template.render_block() method.

RFC: kida-template-introspection
"""

from __future__ import annotations

import pytest

from bengal.rendering.kida import Environment


class TestRenderBlock:
    """Tests for render_block() method."""

    def test_render_simple_block(self):
        """Test rendering a simple block."""
        env = Environment()
        template = env.from_string("""
{% block greeting %}Hello, {{ name }}!{% end %}
""")

        result = template.render_block("greeting", name="World")
        assert result.strip() == "Hello, World!"

    def test_render_block_with_site_context(self):
        """Test rendering a block with site context (common use case)."""
        env = Environment()
        template = env.from_string("""
{% block nav %}
<nav>{{ site.title }}</nav>
{% end %}
""")

        result = template.render_block("nav", site={"title": "My Site"})
        assert "<nav>My Site</nav>" in result

    def test_render_multiple_blocks(self):
        """Test rendering different blocks from same template."""
        env = Environment()
        template = env.from_string("""
{% block header %}<header>{{ title }}</header>{% end %}
{% block footer %}<footer>{{ year }}</footer>{% end %}
""")

        header = template.render_block("header", title="Welcome")
        footer = template.render_block("footer", year=2025)

        assert "<header>Welcome</header>" in header
        assert "<footer>2025</footer>" in footer

    def test_render_block_not_found(self):
        """Test error when block doesn't exist."""
        env = Environment()
        template = env.from_string("{% block existing %}Content{% end %}")

        with pytest.raises(KeyError) as exc_info:
            template.render_block("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "existing" in str(exc_info.value)  # Shows available blocks

    def test_render_block_with_filters(self):
        """Test block with filters."""
        env = Environment()
        template = env.from_string("""
{% block title %}{{ name | upper }}{% end %}
""")

        result = template.render_block("title", name="hello")
        assert "HELLO" in result

    def test_render_block_with_conditionals(self):
        """Test block with conditionals."""
        env = Environment()
        template = env.from_string("""
{% block status %}
{% if active %}Active{% else %}Inactive{% endif %}
{% end %}
""")

        active = template.render_block("status", active=True)
        inactive = template.render_block("status", active=False)

        assert "Active" in active
        assert "Inactive" in inactive

    def test_render_block_with_loop(self):
        """Test block with for loop."""
        env = Environment()
        template = env.from_string("""
{% block items %}
<ul>
{% for item in items %}
<li>{{ item }}</li>
{% end %}
</ul>
{% end %}
""")

        result = template.render_block("items", items=["a", "b", "c"])
        assert "<li>a</li>" in result
        assert "<li>b</li>" in result
        assert "<li>c</li>" in result


class TestListBlocks:
    """Tests for list_blocks() method."""

    def test_list_blocks_empty(self):
        """Test listing blocks from template without blocks."""
        env = Environment()
        template = env.from_string("Just text, no blocks")

        blocks = template.list_blocks()
        assert blocks == []

    def test_list_blocks_single(self):
        """Test listing single block."""
        env = Environment()
        template = env.from_string("{% block only %}Content{% end %}")

        blocks = template.list_blocks()
        assert blocks == ["only"]

    def test_list_blocks_multiple(self):
        """Test listing multiple blocks."""
        env = Environment()
        template = env.from_string("""
{% block alpha %}A{% end %}
{% block beta %}B{% end %}
{% block gamma %}C{% end %}
""")

        blocks = template.list_blocks()
        assert set(blocks) == {"alpha", "beta", "gamma"}


class TestBlockCacheIntegration:
    """Tests for BlockCache with render_block()."""

    def test_block_cache_set_and_get(self):
        """Test basic cache operations."""
        from bengal.rendering.block_cache import BlockCache

        cache = BlockCache()

        # Set a cached block
        cache.set("test.html", "nav", "<nav>Menu</nav>", scope="site")

        # Get it back
        result = cache.get("test.html", "nav")
        assert result == "<nav>Menu</nav>"

    def test_block_cache_stats(self):
        """Test cache statistics."""
        from bengal.rendering.block_cache import BlockCache

        cache = BlockCache()

        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

        # Cache a block
        cache.set("test.html", "nav", "<nav>Menu</nav>", scope="site")
        assert cache.get_stats()["site_blocks_cached"] == 1

        # Hit
        cache.get("test.html", "nav")
        assert cache.get_stats()["hits"] == 1

        # Miss
        cache.get("test.html", "footer")
        assert cache.get_stats()["misses"] == 1

    def test_block_cache_disabled(self):
        """Test cache when disabled."""
        from bengal.rendering.block_cache import BlockCache

        cache = BlockCache(enabled=False)

        cache.set("test.html", "nav", "<nav>Menu</nav>", scope="site")
        result = cache.get("test.html", "nav")

        assert result is None

    def test_block_cache_clear(self):
        """Test cache clearing."""
        from bengal.rendering.block_cache import BlockCache

        cache = BlockCache()
        cache.set("test.html", "nav", "<nav>Menu</nav>", scope="site")

        assert cache.get("test.html", "nav") is not None

        cache.clear()

        assert cache.get("test.html", "nav") is None
        assert cache.get_stats()["site_blocks_cached"] == 0
