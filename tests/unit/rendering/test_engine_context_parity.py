"""
Tests for engine context parity between Jinja2 and Kida.

Ensures both template engines receive identical shared globals
from the centralized get_engine_globals() function.

Related RFC: plan/drafted/rfc-engine-agnostic-context-layer.md
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bengal.rendering.context import (
    ConfigContext,
    MenusContext,
    SiteContext,
    ThemeContext,
)


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site with all required attributes for engine initialization."""
    site = MagicMock()
    site.config = {
        "title": "Test Site",
        "baseurl": "/",
        "development": {"auto_reload": False},
    }
    site.root_path = tmp_path
    site.output_dir = tmp_path / "public"
    site.theme = "default"
    site.theme_config = MagicMock()
    site.theme_config.name = "default"
    site.versioning_enabled = True
    site.versions = [{"name": "v1.0", "latest": True}]
    site.menu = {"main": []}
    site.menu_localized = {}
    site.dev_mode = False

    # Required for template engine initialization
    site._bengal_template_dirs_cache = {}

    return site


class TestEngineParity:
    """Ensure Jinja and Kida get identical shared context."""

    def test_core_globals_present_in_both_engines(self, mock_site, tmp_path):
        """Core globals must be present in both engines."""
        # Import engines
        from bengal.rendering.engines.kida import KidaTemplateEngine

        # Create template directories for Kida
        template_dir = tmp_path / "themes" / "default" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "default.html").write_text("<html>{{ page.title }}</html>")

        # Initialize Kida engine
        kida_engine = KidaTemplateEngine(mock_site)
        kida_globals = set(kida_engine._env.globals.keys())

        # Core globals that must be present
        core_globals = {
            "site",
            "config",
            "theme",
            "bengal",
            "versions",
            "versioning_enabled",
            "getattr",
            "_raw_site",
        }

        assert core_globals <= kida_globals, (
            f"Missing globals in Kida: {core_globals - kida_globals}"
        )

    def test_wrapper_types_in_kida(self, mock_site, tmp_path):
        """Kida engine uses correct wrapper types."""
        from bengal.rendering.engines.kida import KidaTemplateEngine

        # Create template directories for Kida
        template_dir = tmp_path / "themes" / "default" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "default.html").write_text("<html>{{ page.title }}</html>")

        kida_engine = KidaTemplateEngine(mock_site)

        # Check wrapper types
        assert isinstance(kida_engine._env.globals["site"], SiteContext)
        assert isinstance(kida_engine._env.globals["config"], ConfigContext)
        assert isinstance(kida_engine._env.globals["theme"], ThemeContext)
        assert isinstance(kida_engine._env.globals["menus"], MenusContext)

    def test_raw_site_is_actual_site(self, mock_site, tmp_path):
        """_raw_site points to actual site instance."""
        from bengal.rendering.engines.kida import KidaTemplateEngine

        # Create template directories
        template_dir = tmp_path / "themes" / "default" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "default.html").write_text("<html>{{ page.title }}</html>")

        kida_engine = KidaTemplateEngine(mock_site)

        assert kida_engine._env.globals["_raw_site"] is mock_site

    def test_versioning_globals_consistent(self, mock_site, tmp_path):
        """Versioning globals reflect site state."""
        from bengal.rendering.engines.kida import KidaTemplateEngine

        # Create template directories
        template_dir = tmp_path / "themes" / "default" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "default.html").write_text("<html>{{ page.title }}</html>")

        kida_engine = KidaTemplateEngine(mock_site)

        assert kida_engine._env.globals["versioning_enabled"] is True
        assert kida_engine._env.globals["versions"] == [{"name": "v1.0", "latest": True}]

    def test_bengal_metadata_is_dict(self, mock_site, tmp_path):
        """Bengal metadata is a dict with engine info."""
        from bengal.rendering.engines.kida import KidaTemplateEngine

        # Create template directories
        template_dir = tmp_path / "themes" / "default" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "default.html").write_text("<html>{{ page.title }}</html>")

        kida_engine = KidaTemplateEngine(mock_site)
        bengal = kida_engine._env.globals["bengal"]

        assert isinstance(bengal, dict)
        assert "engine" in bengal

    def test_getattr_is_builtin(self, mock_site, tmp_path):
        """getattr global is Python's builtin."""
        from bengal.rendering.engines.kida import KidaTemplateEngine

        # Create template directories
        template_dir = tmp_path / "themes" / "default" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "default.html").write_text("<html>{{ page.title }}</html>")

        kida_engine = KidaTemplateEngine(mock_site)

        assert kida_engine._env.globals["getattr"] is getattr

    def test_engine_specific_globals_present(self, mock_site, tmp_path):
        """Engine-specific globals (url_for, get_menu) are present."""
        from bengal.rendering.engines.kida import KidaTemplateEngine

        # Create template directories
        template_dir = tmp_path / "themes" / "default" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "default.html").write_text("<html>{{ page.title }}</html>")

        kida_engine = KidaTemplateEngine(mock_site)

        # Engine-specific globals
        assert "url_for" in kida_engine._env.globals
        assert "get_menu" in kida_engine._env.globals
        assert "get_menu_lang" in kida_engine._env.globals
        assert callable(kida_engine._env.globals["url_for"])
        assert callable(kida_engine._env.globals["get_menu"])


class TestContextConsistency:
    """Test that context wrappers behave consistently."""

    def test_site_context_provides_safe_access(self, tmp_path):
        """SiteContext provides safe attribute access."""
        from types import SimpleNamespace

        from bengal.rendering.context import SiteContext

        # Create a simple site-like object (not MagicMock, which auto-creates attrs)
        site = SimpleNamespace(
            config={"title": "Test Site"},
            pages=[],
            sections=[],
        )
        site_ctx = SiteContext(site)

        # Should not raise for missing attributes and return config fallback
        assert site_ctx.nonexistent_attr == ""  # Falls back to config.get(name, "")

    def test_config_context_provides_safe_access(self, mock_site, tmp_path):
        """ConfigContext provides safe config access."""
        from bengal.rendering.engines.kida import KidaTemplateEngine

        # Create template directories
        template_dir = tmp_path / "themes" / "default" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "default.html").write_text("<html>{{ page.title }}</html>")

        kida_engine = KidaTemplateEngine(mock_site)
        config_ctx = kida_engine._env.globals["config"]

        # Should access existing config
        assert config_ctx.title == "Test Site"

    def test_theme_context_has_method(self, mock_site, tmp_path):
        """ThemeContext has has() method for feature checking."""
        from bengal.rendering.engines.kida import KidaTemplateEngine

        # Create template directories
        template_dir = tmp_path / "themes" / "default" / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "default.html").write_text("<html>{{ page.title }}</html>")

        kida_engine = KidaTemplateEngine(mock_site)
        theme_ctx = kida_engine._env.globals["theme"]

        # Should have has() method
        assert hasattr(theme_ctx, "has")
        assert callable(theme_ctx.has)
