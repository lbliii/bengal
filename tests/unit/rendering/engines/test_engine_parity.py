"""
Tests for template engine parity between Kida and Jinja2.

These tests ensure that both engines have equivalent behavior and thread-safety
properties, allowing users to swap engines without breaking functionality.

Note: Kida is the primary/default engine, but Jinja2 is still supported
for users who want to use it.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from bengal.core.site import Site


def make_mock_site(
    dev_mode: bool = False,
    theme: str = "default",
    root_path: Path | None = None,
) -> MagicMock:
    """Create a mock site for testing."""
    mock_site = MagicMock()
    mock_site.dev_mode = dev_mode
    mock_site.theme = theme
    mock_site.root_path = root_path or Path("/tmp/test-site")
    mock_site.output_dir = mock_site.root_path / "public"
    mock_site.baseurl = ""
    mock_site.config = {
        "site": {"title": "Test Site"},
        "development": {"dev_mode": dev_mode, "auto_reload": dev_mode},
        "kida": {"bytecode_cache": False},  # Disable for testing
    }
    mock_site.theme_config = MagicMock()
    mock_site.theme_config.config = {}
    mock_site.menu = {}
    mock_site.menu_localized = {}
    mock_site.versioning_enabled = False
    mock_site.versions = []
    mock_site._warned_filters = set()
    mock_site._warned_functions = set()
    mock_site.current_language = None
    return mock_site


class TestEngineCommonInterface:
    """Test that both engines implement the same interface."""

    @pytest.mark.parametrize("engine_type", ["kida", "jinja"])
    def test_render_template_method_exists(self, engine_type: str) -> None:
        """Both engines should have render_template method."""
        mock_site = make_mock_site()

        if engine_type == "kida":
            with patch(
                "bengal.rendering.engines.kida.FileSystemLoader"
            ), patch(
                "bengal.rendering.engines.kida.Environment"
            ):
                from bengal.rendering.engines.kida import KidaTemplateEngine

                engine = KidaTemplateEngine(mock_site)
        else:
            with patch(
                "bengal.rendering.engines.jinja.create_jinja_environment"
            ) as mock_create_env:
                mock_env = MagicMock()
                mock_create_env.return_value = (mock_env, [])

                from bengal.rendering.engines.jinja import JinjaTemplateEngine

                engine = JinjaTemplateEngine(mock_site)

        assert hasattr(engine, "render_template")
        assert callable(engine.render_template)

    @pytest.mark.parametrize("engine_type", ["kida", "jinja"])
    def test_render_string_method_exists(self, engine_type: str) -> None:
        """Both engines should have render_string method."""
        mock_site = make_mock_site()

        if engine_type == "kida":
            with patch(
                "bengal.rendering.engines.kida.FileSystemLoader"
            ), patch(
                "bengal.rendering.engines.kida.Environment"
            ):
                from bengal.rendering.engines.kida import KidaTemplateEngine

                engine = KidaTemplateEngine(mock_site)
        else:
            with patch(
                "bengal.rendering.engines.jinja.create_jinja_environment"
            ) as mock_create_env:
                mock_env = MagicMock()
                mock_create_env.return_value = (mock_env, [])

                from bengal.rendering.engines.jinja import JinjaTemplateEngine

                engine = JinjaTemplateEngine(mock_site)

        assert hasattr(engine, "render_string")
        assert callable(engine.render_string)

    @pytest.mark.parametrize("engine_type", ["kida", "jinja"])
    def test_template_exists_method_exists(self, engine_type: str) -> None:
        """Both engines should have template_exists method."""
        mock_site = make_mock_site()

        if engine_type == "kida":
            with patch(
                "bengal.rendering.engines.kida.FileSystemLoader"
            ), patch(
                "bengal.rendering.engines.kida.Environment"
            ):
                from bengal.rendering.engines.kida import KidaTemplateEngine

                engine = KidaTemplateEngine(mock_site)
        else:
            with patch(
                "bengal.rendering.engines.jinja.create_jinja_environment"
            ) as mock_create_env:
                mock_env = MagicMock()
                mock_create_env.return_value = (mock_env, [])

                from bengal.rendering.engines.jinja import JinjaTemplateEngine

                engine = JinjaTemplateEngine(mock_site)

        assert hasattr(engine, "template_exists")
        assert callable(engine.template_exists)

    @pytest.mark.parametrize("engine_type", ["kida", "jinja"])
    def test_get_template_path_method_exists(self, engine_type: str) -> None:
        """Both engines should have get_template_path method."""
        mock_site = make_mock_site()

        if engine_type == "kida":
            with patch(
                "bengal.rendering.engines.kida.FileSystemLoader"
            ), patch(
                "bengal.rendering.engines.kida.Environment"
            ):
                from bengal.rendering.engines.kida import KidaTemplateEngine

                engine = KidaTemplateEngine(mock_site)
        else:
            with patch(
                "bengal.rendering.engines.jinja.create_jinja_environment"
            ) as mock_create_env:
                mock_env = MagicMock()
                mock_create_env.return_value = (mock_env, [])

                from bengal.rendering.engines.jinja import JinjaTemplateEngine

                engine = JinjaTemplateEngine(mock_site)

        assert hasattr(engine, "get_template_path")
        assert callable(engine.get_template_path)

    @pytest.mark.parametrize("engine_type", ["kida", "jinja"])
    def test_list_templates_method_exists(self, engine_type: str) -> None:
        """Both engines should have list_templates method."""
        mock_site = make_mock_site()

        if engine_type == "kida":
            with patch(
                "bengal.rendering.engines.kida.FileSystemLoader"
            ), patch(
                "bengal.rendering.engines.kida.Environment"
            ):
                from bengal.rendering.engines.kida import KidaTemplateEngine

                engine = KidaTemplateEngine(mock_site)
        else:
            with patch(
                "bengal.rendering.engines.jinja.create_jinja_environment"
            ) as mock_create_env:
                mock_env = MagicMock()
                mock_create_env.return_value = (mock_env, [])

                from bengal.rendering.engines.jinja import JinjaTemplateEngine

                engine = JinjaTemplateEngine(mock_site)

        assert hasattr(engine, "list_templates")
        assert callable(engine.list_templates)


class TestEngineDependencyTracking:
    """Test that both engines support dependency tracking."""

    @pytest.mark.parametrize("engine_type", ["kida", "jinja"])
    def test_dependency_tracker_attribute_exists(self, engine_type: str) -> None:
        """Both engines should have _dependency_tracker attribute."""
        mock_site = make_mock_site()

        if engine_type == "kida":
            with patch(
                "bengal.rendering.engines.kida.FileSystemLoader"
            ), patch(
                "bengal.rendering.engines.kida.Environment"
            ):
                from bengal.rendering.engines.kida import KidaTemplateEngine

                engine = KidaTemplateEngine(mock_site)
        else:
            with patch(
                "bengal.rendering.engines.jinja.create_jinja_environment"
            ) as mock_create_env:
                mock_env = MagicMock()
                mock_create_env.return_value = (mock_env, [])

                from bengal.rendering.engines.jinja import JinjaTemplateEngine

                engine = JinjaTemplateEngine(mock_site)

        assert hasattr(engine, "_dependency_tracker")
        # Initially None
        assert engine._dependency_tracker is None

    @pytest.mark.parametrize("engine_type", ["kida", "jinja"])
    def test_dependency_tracker_can_be_set(self, engine_type: str) -> None:
        """Both engines should allow setting _dependency_tracker."""
        mock_site = make_mock_site()
        mock_tracker = MagicMock()

        if engine_type == "kida":
            with patch(
                "bengal.rendering.engines.kida.FileSystemLoader"
            ), patch(
                "bengal.rendering.engines.kida.Environment"
            ):
                from bengal.rendering.engines.kida import KidaTemplateEngine

                engine = KidaTemplateEngine(mock_site)
        else:
            with patch(
                "bengal.rendering.engines.jinja.create_jinja_environment"
            ) as mock_create_env:
                mock_env = MagicMock()
                mock_create_env.return_value = (mock_env, [])

                from bengal.rendering.engines.jinja import JinjaTemplateEngine

                engine = JinjaTemplateEngine(mock_site)

        engine._dependency_tracker = mock_tracker
        assert engine._dependency_tracker is mock_tracker


class TestEngineMenuCache:
    """Test that both engines have menu caching."""

    @pytest.mark.parametrize("engine_type", ["kida", "jinja"])
    def test_invalidate_menu_cache_method_exists(self, engine_type: str) -> None:
        """Both engines should have invalidate_menu_cache method."""
        mock_site = make_mock_site()

        if engine_type == "kida":
            with patch(
                "bengal.rendering.engines.kida.FileSystemLoader"
            ), patch(
                "bengal.rendering.engines.kida.Environment"
            ):
                from bengal.rendering.engines.kida import KidaTemplateEngine

                engine = KidaTemplateEngine(mock_site)
        else:
            with patch(
                "bengal.rendering.engines.jinja.create_jinja_environment"
            ) as mock_create_env:
                mock_env = MagicMock()
                mock_create_env.return_value = (mock_env, [])

                from bengal.rendering.engines.jinja import JinjaTemplateEngine

                engine = JinjaTemplateEngine(mock_site)

        assert hasattr(engine, "invalidate_menu_cache")
        assert callable(engine.invalidate_menu_cache)

    @pytest.mark.parametrize("engine_type", ["kida", "jinja"])
    def test_menu_dict_cache_attribute_exists(self, engine_type: str) -> None:
        """Both engines should have _menu_dict_cache attribute."""
        mock_site = make_mock_site()

        if engine_type == "kida":
            with patch(
                "bengal.rendering.engines.kida.FileSystemLoader"
            ), patch(
                "bengal.rendering.engines.kida.Environment"
            ):
                from bengal.rendering.engines.kida import KidaTemplateEngine

                engine = KidaTemplateEngine(mock_site)
        else:
            with patch(
                "bengal.rendering.engines.jinja.create_jinja_environment"
            ) as mock_create_env:
                mock_env = MagicMock()
                mock_create_env.return_value = (mock_env, [])

                from bengal.rendering.engines.jinja import JinjaTemplateEngine

                engine = JinjaTemplateEngine(mock_site)

        assert hasattr(engine, "_menu_dict_cache")
        assert isinstance(engine._menu_dict_cache, dict)


class TestEngineCapabilities:
    """Test engine capabilities reporting."""

    def test_kida_has_advanced_capabilities(self) -> None:
        """Verify Kida reports advanced capabilities."""
        mock_site = make_mock_site()

        with patch(
            "bengal.rendering.engines.kida.FileSystemLoader"
        ), patch(
            "bengal.rendering.engines.kida.Environment"
        ):
            from bengal.rendering.engines.kida import KidaTemplateEngine
            from bengal.protocols import EngineCapability

            engine = KidaTemplateEngine(mock_site)

        # Kida should have advanced capabilities
        assert engine.has_capability(EngineCapability.BLOCK_CACHING)
        assert engine.has_capability(EngineCapability.INTROSPECTION)

    def test_jinja_has_no_advanced_capabilities(self) -> None:
        """Verify Jinja2 reports no advanced capabilities."""
        mock_site = make_mock_site()

        with patch(
            "bengal.rendering.engines.jinja.create_jinja_environment"
        ) as mock_create_env:
            mock_env = MagicMock()
            mock_create_env.return_value = (mock_env, [])

            from bengal.rendering.engines.jinja import JinjaTemplateEngine
            from bengal.protocols import EngineCapability

            engine = JinjaTemplateEngine(mock_site)

        # Jinja2 doesn't have advanced capabilities
        assert not engine.has_capability(EngineCapability.BLOCK_CACHING)
        assert not engine.has_capability(EngineCapability.INTROSPECTION)

    @pytest.mark.parametrize("engine_type", ["kida", "jinja"])
    def test_capabilities_property_exists(self, engine_type: str) -> None:
        """Both engines should have capabilities property."""
        mock_site = make_mock_site()

        if engine_type == "kida":
            with patch(
                "bengal.rendering.engines.kida.FileSystemLoader"
            ), patch(
                "bengal.rendering.engines.kida.Environment"
            ):
                from bengal.rendering.engines.kida import KidaTemplateEngine

                engine = KidaTemplateEngine(mock_site)
        else:
            with patch(
                "bengal.rendering.engines.jinja.create_jinja_environment"
            ) as mock_create_env:
                mock_env = MagicMock()
                mock_create_env.return_value = (mock_env, [])

                from bengal.rendering.engines.jinja import JinjaTemplateEngine

                engine = JinjaTemplateEngine(mock_site)

        assert hasattr(engine, "capabilities")

    @pytest.mark.parametrize("engine_type", ["kida", "jinja"])
    def test_has_capability_method_exists(self, engine_type: str) -> None:
        """Both engines should have has_capability method."""
        mock_site = make_mock_site()

        if engine_type == "kida":
            with patch(
                "bengal.rendering.engines.kida.FileSystemLoader"
            ), patch(
                "bengal.rendering.engines.kida.Environment"
            ):
                from bengal.rendering.engines.kida import KidaTemplateEngine

                engine = KidaTemplateEngine(mock_site)
        else:
            with patch(
                "bengal.rendering.engines.jinja.create_jinja_environment"
            ) as mock_create_env:
                mock_env = MagicMock()
                mock_create_env.return_value = (mock_env, [])

                from bengal.rendering.engines.jinja import JinjaTemplateEngine

                engine = JinjaTemplateEngine(mock_site)

        assert hasattr(engine, "has_capability")
        assert callable(engine.has_capability)
