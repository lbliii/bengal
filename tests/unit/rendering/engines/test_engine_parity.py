"""
Tests for the Kida template engine interface.

These tests verify that the Kida engine correctly implements the
TemplateEngineProtocol interface.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from bengal.rendering.context.lazy import LazyPageContext, make_lazy


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


def make_kida_engine(mock_site: MagicMock):
    """Create a KidaTemplateEngine with mocked environment for testing."""
    with (
        patch("bengal.rendering.engines.kida.FileSystemLoader"),
        patch("bengal.rendering.engines.kida.Environment"),
    ):
        from bengal.rendering.engines.kida import KidaTemplateEngine

        return KidaTemplateEngine(mock_site)


class TestEngineCommonInterface:
    """Test that the Kida engine implements the required interface."""

    def test_render_template_method_exists(self) -> None:
        """Engine should have render_template method."""
        mock_site = make_mock_site()
        engine = make_kida_engine(mock_site)
        assert hasattr(engine, "render_template")
        assert callable(engine.render_template)

    def test_render_string_method_exists(self) -> None:
        """Engine should have render_string method."""
        mock_site = make_mock_site()
        engine = make_kida_engine(mock_site)
        assert hasattr(engine, "render_string")
        assert callable(engine.render_string)

    def test_template_exists_method_exists(self) -> None:
        """Engine should have template_exists method."""
        mock_site = make_mock_site()
        engine = make_kida_engine(mock_site)
        assert hasattr(engine, "template_exists")
        assert callable(engine.template_exists)

    def test_get_template_path_method_exists(self) -> None:
        """Engine should have get_template_path method."""
        mock_site = make_mock_site()
        engine = make_kida_engine(mock_site)
        assert hasattr(engine, "get_template_path")
        assert callable(engine.get_template_path)

    def test_list_templates_method_exists(self) -> None:
        """Engine should have list_templates method."""
        mock_site = make_mock_site()
        engine = make_kida_engine(mock_site)
        assert hasattr(engine, "list_templates")
        assert callable(engine.list_templates)


class TestEngineMenuCache:
    """Test that the Kida engine has menu caching."""

    def test_invalidate_menu_cache_method_exists(self) -> None:
        """Engine should have invalidate_menu_cache method."""
        mock_site = make_mock_site()
        engine = make_kida_engine(mock_site)
        assert hasattr(engine, "invalidate_menu_cache")
        assert callable(engine.invalidate_menu_cache)

    def test_menu_dict_cache_attribute_exists(self) -> None:
        """Engine should have _menu_dict_cache attribute."""
        mock_site = make_mock_site()
        engine = make_kida_engine(mock_site)
        assert hasattr(engine, "_menu_dict_cache")
        assert isinstance(engine._menu_dict_cache, dict)


class TestKidaLazyContext:
    """Kida rendering preserves Bengal lazy template context values."""

    def test_render_template_does_not_evaluate_unused_lazy_value(self, tmp_path: Path) -> None:
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "page.html").write_text("{{ title }}", encoding="utf-8")
        site = make_mock_site(root_path=tmp_path)
        site.theme = ""

        from bengal.rendering.engines.kida import KidaTemplateEngine

        engine = KidaTemplateEngine(site)
        context = LazyPageContext(
            {
                "title": "Hello",
                "posts": make_lazy(
                    lambda: (_ for _ in ()).throw(AssertionError("unused lazy value was evaluated"))
                ),
            }
        )

        assert engine.render_template("page.html", context) == "Hello"

    def test_render_template_evaluates_used_lazy_value(self, tmp_path: Path) -> None:
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "page.html").write_text("{{ posts | length }}", encoding="utf-8")
        site = make_mock_site(root_path=tmp_path)
        site.theme = ""

        from bengal.rendering.engines.kida import KidaTemplateEngine

        engine = KidaTemplateEngine(site)
        context = LazyPageContext({"posts": make_lazy(lambda: ["one", "two"])})

        assert engine.render_template("page.html", context) == "2"


class TestEngineCapabilities:
    """Test engine capabilities reporting."""

    def test_kida_has_advanced_capabilities(self) -> None:
        """Verify Kida reports advanced capabilities."""
        mock_site = make_mock_site()
        engine = make_kida_engine(mock_site)

        from bengal.protocols import EngineCapability

        assert engine.has_capability(EngineCapability.BLOCK_CACHING)
        assert engine.has_capability(EngineCapability.INTROSPECTION)

    def test_capabilities_property_exists(self) -> None:
        """Engine should have capabilities property."""
        mock_site = make_mock_site()
        engine = make_kida_engine(mock_site)
        assert hasattr(engine, "capabilities")

    def test_has_capability_method_exists(self) -> None:
        """Engine should have has_capability method."""
        mock_site = make_mock_site()
        engine = make_kida_engine(mock_site)
        assert hasattr(engine, "has_capability")
        assert callable(engine.has_capability)
