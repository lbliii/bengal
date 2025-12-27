"""Tests for Kida auto_reload functionality.

Tests that templates are automatically reloaded when source changes,
using hash-based cache invalidation.
"""

from __future__ import annotations

from bengal.rendering.kida import Environment
from bengal.rendering.kida.environment.loaders import DictLoader, FileSystemLoader


class TestAutoReload:
    """Tests for auto_reload template cache invalidation."""

    def test_auto_reload_detects_source_changes(self) -> None:
        """Template cache invalidates when source changes with auto_reload=True."""
        # Create loader with mutable template source
        templates = {"test.html": "Hello, {{ name }}!"}
        loader = DictLoader(templates)
        env = Environment(loader=loader, auto_reload=True)

        # Load template (cached)
        t1 = env.get_template("test.html")
        result1 = t1.render(name="World")
        assert result1 == "Hello, World!"

        # Change source
        templates["test.html"] = "Hi, {{ name }}!"

        # Reload template (should detect change and recompile)
        t2 = env.get_template("test.html")
        result2 = t2.render(name="World")
        assert result2 == "Hi, World!"

        # Should be different template objects (recompiled)
        assert t1 is not t2

    def test_auto_reload_false_uses_cached_template(self) -> None:
        """With auto_reload=False, cached template is returned even if source changed."""
        templates = {"test.html": "Hello, {{ name }}!"}
        loader = DictLoader(templates)
        env = Environment(loader=loader, auto_reload=False)

        # Load template (cached)
        t1 = env.get_template("test.html")
        result1 = t1.render(name="World")
        assert result1 == "Hello, World!"

        # Change source
        templates["test.html"] = "Hi, {{ name }}!"

        # Reload template (should return cached version)
        t2 = env.get_template("test.html")
        result2 = t2.render(name="World")
        assert result2 == "Hello, World!"  # Still old version

        # Should be same template object (cached)
        assert t1 is t2

    def test_auto_reload_defaults_to_true(self) -> None:
        """auto_reload defaults to True."""
        loader = DictLoader({"test.html": "Hello"})
        env = Environment(loader=loader)
        assert env.auto_reload is True

    def test_auto_reload_with_filesystem_loader(self, tmp_path) -> None:
        """auto_reload works with FileSystemLoader."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.html"
        template_file.write_text("Hello, {{ name }}!")

        loader = FileSystemLoader(template_dir)
        env = Environment(loader=loader, auto_reload=True)

        # Load template
        t1 = env.get_template("test.html")
        result1 = t1.render(name="World")
        assert result1 == "Hello, World!"

        # Change file
        template_file.write_text("Hi, {{ name }}!")

        # Reload template (should detect change)
        t2 = env.get_template("test.html")
        result2 = t2.render(name="World")
        assert result2 == "Hi, World!"

        # Should be different template objects
        assert t1 is not t2

    def test_clear_template_cache_all(self) -> None:
        """clear_template_cache() clears all templates when names=None."""
        loader = DictLoader({"a.html": "A", "b.html": "B"})
        env = Environment(loader=loader, auto_reload=True)

        # Load templates
        ta1 = env.get_template("a.html")
        tb1 = env.get_template("b.html")

        # Clear all cache
        env.clear_template_cache()

        # Reload templates (should be new objects)
        ta2 = env.get_template("a.html")
        tb2 = env.get_template("b.html")

        assert ta1 is not ta2
        assert tb1 is not tb2

    def test_clear_template_cache_specific(self) -> None:
        """clear_template_cache() clears specific templates when names provided."""
        loader = DictLoader({"a.html": "A", "b.html": "B"})
        env = Environment(loader=loader, auto_reload=True)

        # Load templates
        ta1 = env.get_template("a.html")
        tb1 = env.get_template("b.html")

        # Clear only "a.html"
        env.clear_template_cache(["a.html"])

        # Reload templates
        ta2 = env.get_template("a.html")  # Should be new (cleared)
        tb2 = env.get_template("b.html")  # Should be cached (not cleared)

        assert ta1 is not ta2
        assert tb1 is tb2  # Same object (still cached)

    def test_clear_template_cache_handles_missing_names(self) -> None:
        """clear_template_cache() handles non-existent template names gracefully."""
        loader = DictLoader({"test.html": "Hello"})
        env = Environment(loader=loader)

        # Should not raise error
        env.clear_template_cache(["missing.html", "test.html"])

        # Template should still work
        result = env.get_template("test.html").render()
        assert result == "Hello"
