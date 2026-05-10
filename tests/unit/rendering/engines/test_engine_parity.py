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

    def test_validate_security_reports_kida_static_findings(self, tmp_path: Path) -> None:
        """Kida 0.9 static analysis should surface trust-boundary warnings."""
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "page.html").write_text(
            "{{ user.password | safe }}",
            encoding="utf-8",
        )
        site = make_mock_site(root_path=tmp_path)
        site.theme = ""

        from bengal.rendering.engines.kida import KidaTemplateEngine

        engine = KidaTemplateEngine(site)
        findings = engine.validate_security(["page.html"])

        codes = {finding.diagnostic_code for finding in findings}
        assert "K-ESC-002" in codes
        assert "K-PRI-001" in codes
        assert all(finding.severity == "warning" for finding in findings)
        assert any("safe" in (finding.suggestion or "") for finding in findings)


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

    def test_render_template_preserves_environment_globals(self, tmp_path: Path) -> None:
        templates = tmp_path / "templates"
        templates.mkdir()
        (templates / "page.html").write_text("{{ bengal.engine.name }}", encoding="utf-8")
        site = make_mock_site(root_path=tmp_path)
        site.theme = ""

        from bengal.rendering.engines.kida import KidaTemplateEngine

        engine = KidaTemplateEngine(site)

        assert engine.render_template("page.html", {}) == "Bengal SSG"


class TestKidaTemplateDependencyCache:
    """Template dependency graph discovery is cached per engine."""

    def test_dependency_discovery_cached_but_recording_repeats(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        site = make_mock_site(root_path=tmp_path)

        from bengal.rendering.engines.kida import KidaTemplateEngine

        engine = KidaTemplateEngine(site)
        dependency_calls: dict[str, int] = {"page.html": 0, "partial.html": 0}

        class FakeTemplate:
            def __init__(self, name: str) -> None:
                self.name = name

            def dependencies(self) -> dict[str, list[str]]:
                dependency_calls[self.name] += 1
                if self.name == "page.html":
                    return {"includes": ["partial.html"]}
                return {}

        def get_template(name: str) -> FakeTemplate:
            return FakeTemplate(name)

        recorded_includes: list[str] = []
        recorded_paths: list[Path] = []

        monkeypatch.setattr(engine._env, "get_template", get_template)
        monkeypatch.setattr(
            KidaTemplateEngine, "get_template_path", lambda _self, name: tmp_path / name
        )
        monkeypatch.setattr(
            "bengal.effects.render_integration.record_template_include",
            recorded_includes.append,
        )
        monkeypatch.setattr(
            "bengal.effects.render_integration.record_extra_dependency",
            recorded_paths.append,
        )

        engine._track_referenced_templates("page.html")
        engine._track_referenced_templates("page.html")

        assert dependency_calls == {"page.html": 1, "partial.html": 1}
        assert recorded_includes == ["partial.html", "partial.html"]
        assert recorded_paths == [tmp_path / "partial.html", tmp_path / "partial.html"]


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
