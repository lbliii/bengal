"""
Tests for template inheritance change detection.

Verifies that changes to parent templates in the theme chain are properly
detected and cause re-rendering rather than serving stale cached output.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestThemeChainResolution:
    """Test theme chain resolution for template inheritance."""

    def test_resolve_theme_chain_returns_ordered_themes(self, tmp_path):
        """
        resolve_theme_chain should return themes in child-to-parent order.
        """
        from bengal.rendering.template_engine.environment import resolve_theme_chain

        # Create site mock with theme directories
        site = MagicMock()
        site.root_path = tmp_path

        # Create themes directory structure
        themes_dir = tmp_path / "themes"
        
        # Parent theme
        parent_theme = themes_dir / "parent"
        parent_theme.mkdir(parents=True)
        (parent_theme / "theme.toml").write_text('[theme]\nname = "parent"\n')

        # Child theme extends parent
        child_theme = themes_dir / "child"
        child_theme.mkdir(parents=True)
        (child_theme / "theme.toml").write_text(
            '[theme]\nname = "child"\nextends = "parent"\n'
        )

        # Patch the theme package lookup to return None (no installed themes)
        with patch(
            "bengal.rendering.template_engine.environment.get_theme_package",
            return_value=None,
        ):
            chain = resolve_theme_chain("child", site)

        # Child should come first, parent second
        assert len(chain) >= 1
        assert chain[0] == "child"
        if len(chain) > 1:
            assert chain[1] == "parent"


class TestParentTemplateChanges:
    """Test detection of changes to parent templates."""

    def test_jinja_auto_reload_detects_parent_changes(self, tmp_path):
        """
        Jinja2 auto_reload should detect changes to parent templates.
        
        When a child template extends a parent and the parent changes,
        Jinja2's auto_reload feature (enabled in dev mode) should detect
        the parent's mtime change and recompile.
        """
        from jinja2 import Environment, FileSystemLoader

        # Create parent template
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        parent = templates_dir / "base.html"
        parent.write_text("<html>Version 1</html>")

        # Create child template
        child = templates_dir / "page.html"
        child.write_text("{% extends 'base.html' %}")

        # Create environment with auto_reload
        env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            auto_reload=True,
        )

        # First render
        template = env.get_template("page.html")
        result1 = template.render()
        assert "Version 1" in result1

        # Modify parent template
        import time

        time.sleep(0.1)  # Ensure mtime changes
        parent.write_text("<html>Version 2</html>")

        # Re-get template (auto_reload should detect change)
        template = env.get_template("page.html")
        result2 = template.render()
        assert "Version 2" in result2


class TestIncludeAndMacroChanges:
    """Test detection of changes to included templates and macros."""

    def test_included_template_changes_detected(self, tmp_path):
        """Changes to included templates should be detected in dev mode."""
        from jinja2 import Environment, FileSystemLoader

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create included partial
        partial = templates_dir / "_header.html"
        partial.write_text("<header>Header v1</header>")

        # Create main template that includes partial
        main = templates_dir / "page.html"
        main.write_text('<div>{% include "_header.html" %}</div>')

        env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            auto_reload=True,
        )

        # First render
        template = env.get_template("page.html")
        result1 = template.render()
        assert "Header v1" in result1

        # Modify partial
        import time

        time.sleep(0.1)
        partial.write_text("<header>Header v2</header>")

        # Re-render should pick up change
        template = env.get_template("page.html")
        result2 = template.render()
        assert "Header v2" in result2

    def test_macro_file_changes_detected(self, tmp_path):
        """Changes to macro files should be detected in dev mode."""
        from jinja2 import Environment, FileSystemLoader

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create macro file
        macros = templates_dir / "_macros.html"
        macros.write_text("{% macro greeting() %}Hello v1{% endmacro %}")

        # Create template using macro
        main = templates_dir / "page.html"
        main.write_text(
            '{% from "_macros.html" import greeting %}<div>{{ greeting() }}</div>'
        )

        env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            auto_reload=True,
        )

        # First render
        template = env.get_template("page.html")
        result1 = template.render()
        assert "Hello v1" in result1

        # Modify macro
        import time

        time.sleep(0.1)
        macros.write_text("{% macro greeting() %}Hello v2{% endmacro %}")

        # Re-render should pick up change
        template = env.get_template("page.html")
        result2 = template.render()
        assert "Hello v2" in result2


class TestDevModeEnsuresAutoReload:
    """Test that dev mode properly enables auto_reload."""

    def test_dev_server_config_enables_auto_reload(self, tmp_path):
        """
        When dev_server=True in config, Jinja environment should have auto_reload=True.
        
        This ensures template file changes are detected during development.
        """
        from unittest.mock import MagicMock, patch
        from bengal.rendering.template_engine.environment import create_jinja_environment

        site = MagicMock()
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"
        site.output_dir.mkdir(parents=True, exist_ok=True)
        site.config = {"dev_server": True}
        site.theme = None
        site.theme_config = {}

        mock_engine = MagicMock()

        with patch(
            "bengal.rendering.template_engine.environment.register_all"
        ):
            env, _ = create_jinja_environment(site, mock_engine, profile_templates=False)

        assert env.auto_reload is True, "auto_reload should be True in dev server mode"

    def test_production_mode_disables_auto_reload(self, tmp_path):
        """
        When dev_server=False in config, auto_reload should be disabled for performance.
        """
        from unittest.mock import MagicMock, patch
        from bengal.rendering.template_engine.environment import create_jinja_environment

        site = MagicMock()
        site.root_path = tmp_path
        site.output_dir = tmp_path / "public"
        site.output_dir.mkdir(parents=True, exist_ok=True)
        site.config = {"dev_server": False, "cache_templates": False}  # No bytecode cache needed
        site.theme = None
        site.theme_config = {}

        mock_engine = MagicMock()

        with patch(
            "bengal.rendering.template_engine.environment.register_all"
        ):
            env, _ = create_jinja_environment(site, mock_engine, profile_templates=False)

        assert env.auto_reload is False, "auto_reload should be False in production mode"
