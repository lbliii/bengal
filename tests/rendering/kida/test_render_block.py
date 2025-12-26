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


class TestBlockCacheIntrospection:
    """Tests for BlockCache with Kida introspection."""

    def test_introspection_detects_site_scoped_blocks(self):
        """Test that site-scoped blocks are detected correctly."""
        from bengal.rendering.kida import Environment

        env = Environment(preserve_ast=True, bytecode_cache=False)

        # Add pure functions
        for fn in ["current_lang", "get_menu", "icon", "asset_url", "t"]:
            env.add_global(fn, lambda *args, **kwargs: "mock")
        for flt in ["dateformat", "absolute_url", "default"]:
            env.add_filter(flt, lambda x, *args, **kwargs: x)

        # Template with site-scoped and page-scoped blocks
        template = env.from_string("""
{% block site_header %}
<header>{{ config.title }}</header>
{% end %}

{% block page_content %}
<main>{{ page.title }}</main>
{% end %}
""")

        meta = template.template_metadata()
        assert meta is not None
        assert "site_header" in meta.blocks
        assert "page_content" in meta.blocks

        # site_header only uses config.* (site-scoped)
        assert meta.blocks["site_header"].cache_scope == "site"
        # page_content uses page.* (page-scoped)
        assert meta.blocks["page_content"].cache_scope == "page"

    def test_bytecode_cache_preserves_ast_for_introspection(self):
        """Test that AST is preserved when loading from bytecode cache."""
        import tempfile
        from pathlib import Path

        from bengal.rendering.kida import Environment, FileSystemLoader
        from bengal.rendering.kida.bytecode_cache import BytecodeCache

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a template file
            template_dir = Path(tmpdir) / "templates"
            template_dir.mkdir()
            (template_dir / "test.html").write_text("""
{% block site_nav %}
<nav>{{ site.title }}</nav>
{% end %}
""")
            cache_dir = Path(tmpdir) / "cache"

            # First load - compiles and caches
            env1 = Environment(
                loader=FileSystemLoader(str(template_dir)),
                preserve_ast=True,
                bytecode_cache=BytecodeCache(cache_dir),
            )
            template1 = env1.get_template("test.html")
            meta1 = template1.template_metadata()
            assert meta1 is not None
            assert "site_nav" in meta1.blocks
            assert meta1.blocks["site_nav"].cache_scope == "site"

            # Second load - from bytecode cache
            env2 = Environment(
                loader=FileSystemLoader(str(template_dir)),
                preserve_ast=True,
                bytecode_cache=BytecodeCache(cache_dir),
            )
            template2 = env2.get_template("test.html")
            meta2 = template2.template_metadata()

            # AST should be preserved even from bytecode cache
            assert meta2 is not None, "AST should be restored when loading from bytecode cache"
            assert "site_nav" in meta2.blocks
            assert meta2.blocks["site_nav"].cache_scope == "site"

    def test_block_cache_warm_site_blocks(self):
        """Test warming site blocks from a template."""
        import tempfile
        from pathlib import Path

        from bengal.rendering.block_cache import BlockCache
        from bengal.rendering.kida import Environment, FileSystemLoader

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a template file
            template_dir = Path(tmpdir) / "templates"
            template_dir.mkdir()
            (template_dir / "base.html").write_text("""
{% block site_footer %}
<footer>© {{ config.title }}</footer>
{% end %}
""")

            env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                preserve_ast=True,
                bytecode_cache=False,
            )

            # Add required functions/filters
            env.add_global("site", {"title": "Test Site", "build_time": "2025-01-01"})
            env.add_global("config", {"title": "Test Site"})
            for fn in ["current_lang", "get_menu", "icon", "asset_url", "t"]:
                env.add_global(fn, lambda *args, **kwargs: "mock")
            for flt in ["dateformat", "absolute_url", "default"]:
                env.add_filter(flt, lambda x, *args, **kwargs: x)

            # Mock engine for BlockCache
            class MockEngine:
                def __init__(self, env):
                    self.env = env

                def get_cacheable_blocks(self, name):
                    try:
                        template = self.env.get_template(name)
                        meta = template.template_metadata()
                        if not meta:
                            return {}
                        return {
                            n: b.cache_scope
                            for n, b in meta.blocks.items()
                            if b.cache_scope in ("site", "page") and b.is_pure == "pure"
                        }
                    except Exception:
                        return {}

            # Warm the cache
            cache = BlockCache(enabled=True)
            engine = MockEngine(env)

            count = cache.warm_site_blocks(
                engine,
                "base.html",
                {
                    "site": {"title": "Test Site", "build_time": "2025-01-01"},
                    "config": {"title": "Test Site"},
                },
            )

            assert count == 1, f"Expected 1 block cached, got {count}"
            assert cache.get_stats()["site_blocks_cached"] == 1

            # Verify cached HTML
            cached = cache.get("base.html", "site_footer")
            assert cached is not None
            assert "Test Site" in cached
            assert cache.get_stats()["hits"] == 1

    def test_default_template_cacheable_blocks(self):
        """Test that default base.html has expected cacheable blocks.

        This tests the full integration with the real KidaTemplateEngine,
        which has all the filters, tests, and globals properly registered.
        """
        from pathlib import Path

        from bengal.rendering.kida import Environment, FileSystemLoader

        # Find the default templates
        bengal_root = Path(__file__).parent.parent.parent.parent
        template_dir = bengal_root / "bengal" / "themes" / "default" / "templates"

        if not template_dir.exists():
            pytest.skip("Default templates not found")

        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            preserve_ast=True,
            bytecode_cache=False,
        )

        # Add minimal globals and filters needed for compilation
        env.add_global(
            "site", {"title": "Test", "build_badge": "abc123", "link_previews": {"enabled": False}}
        )
        env.add_global(
            "config",
            {"title": "Test", "search": {}, "assets": {"bundle_js": False}, "output_formats": {}},
        )
        env.add_global("page", {"title": "Test Page", "is_draft": False, "is_featured": False})
        env.add_global("theme", {"features": []})

        # Register all functions needed for compilation
        for fn in [
            "current_lang",
            "get_menu_lang",
            "get_menu",
            "icon",
            "asset_url",
            "t",
            "absolute_url",
            "canonical_url",
            "og_image",
            "bengal",
            "get_auto_nav",
            "alternate_links",
            "relative_url",
            "build_artifact_url",
        ]:
            env.add_global(fn, lambda *args, **kwargs: "mock")

        # Register all filters needed for compilation
        for flt in [
            "dateformat",
            "absolute_url",
            "default",
            "tojson",
            "meta_keywords",
            "meta_description",
            "safe",
            "escape",
            "slugify",
            "truncate",
            "title",
            "lower",
            "upper",
            "join",
            "length",
            "first",
            "last",
            "sort",
            "reverse",
            "unique",
            "selectattr",
            "rejectattr",
            "map",
            "list",
            "dictsort",
            "e",
            "md",
            "markdown",
            "format",
            "striptags",
        ]:
            env.add_filter(flt, lambda x, *args, **kwargs: x)

        # Register all tests needed for compilation
        for test in [
            "draft",
            "featured",
            "outdated",
            "defined",
            "undefined",
            "none",
            "callable",
            "mapping",
            "iterable",
            "sequence",
            "string",
            "number",
        ]:
            env.add_test(test, lambda x, *args, **kwargs: False)

        # Load and analyze base.html
        try:
            template = env.get_template("base.html")
        except Exception as e:
            pytest.skip(f"Could not load base.html: {e}")

        meta = template.template_metadata()
        assert meta is not None, "Template metadata should be available"
        assert len(meta.blocks) > 0, "Template should have blocks"

        # Verify our key site-scoped blocks exist
        expected_site_blocks = ["site_footer", "site_search_modal", "site_scripts", "site_dialogs"]
        found_site_blocks = []

        for block_name, block_meta in meta.blocks.items():
            if block_name in expected_site_blocks:
                found_site_blocks.append(block_name)
                # These should be site-scoped and pure
                assert block_meta.cache_scope == "site", (
                    f"{block_name} should be site-scoped, got {block_meta.cache_scope}"
                )
                assert block_meta.is_pure == "pure", (
                    f"{block_name} should be pure, got {block_meta.is_pure}"
                )

        # At least some of our expected blocks should be found
        assert len(found_site_blocks) >= 2, (
            f"Expected at least 2 of {expected_site_blocks}, found {found_site_blocks}"
        )
