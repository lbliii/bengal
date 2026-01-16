"""
Integration smoke tests for debug tools.

Ensures debug tools work correctly with real Site objects and don't
crash on typical usage patterns.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.debug import (
    BuildDeltaAnalyzer,
    ConfigInspector,
    ContentMigrator,
    DependencyVisualizer,
    IncrementalBuildDebugger,
    PageExplainer,
    ShortcodeSandbox,
)


class TestDebugToolsInstantiation:
    """Verify debug tools can be instantiated without errors."""

    @pytest.fixture
    def test_site_root(self, tmp_path: Path) -> Path:
        """Create a minimal test site structure."""
        # Create config directory
        config_dir = tmp_path / "config" / "_default"
        config_dir.mkdir(parents=True)
        (config_dir / "site.yaml").write_text("site:\n  title: Test Site\n")

        # Create content directory
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home\n")
        (content_dir / "about.md").write_text("---\ntitle: About\n---\n# About\n")

        # Create templates directory
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "base.html").write_text("<html>{% block content %}{% endblock %}</html>")
        (templates_dir / "page.html").write_text('{% extends "base.html" %}{% block content %}{{ page.content }}{% endblock %}')

        return tmp_path

    def test_config_inspector_instantiation(self, test_site_root: Path) -> None:
        """ConfigInspector creates without errors."""
        from unittest.mock import MagicMock

        mock_site = MagicMock()
        mock_site.root_path = test_site_root
        mock_site.config = {"site": {"title": "Test"}}

        inspector = ConfigInspector(site=mock_site)

        assert inspector.site is mock_site
        assert inspector._config_dir == test_site_root / "config"

    def test_content_migrator_instantiation(self, test_site_root: Path) -> None:
        """ContentMigrator creates without errors."""
        from unittest.mock import MagicMock

        mock_site = MagicMock()
        mock_site.root_path = test_site_root
        mock_site.pages = []

        migrator = ContentMigrator(site=mock_site, root_path=test_site_root)

        assert migrator.site is mock_site
        assert migrator.root_path == test_site_root

    def test_page_explainer_instantiation(self, test_site_root: Path) -> None:
        """PageExplainer creates without errors."""
        from unittest.mock import MagicMock

        mock_site = MagicMock()
        mock_site.root_path = test_site_root
        mock_site.output_dir = test_site_root / "public"
        mock_site.pages = []

        explainer = PageExplainer(site=mock_site)

        assert explainer.site is mock_site

    def test_incremental_debugger_instantiation(self) -> None:
        """IncrementalBuildDebugger creates without errors."""
        from unittest.mock import MagicMock

        mock_cache = MagicMock()
        mock_cache.file_fingerprints = {}
        mock_cache.dependencies = {}
        mock_cache.taxonomy_deps = {}

        debugger = IncrementalBuildDebugger(cache=mock_cache)

        assert debugger.cache is mock_cache

    def test_build_delta_analyzer_instantiation(self, test_site_root: Path) -> None:
        """BuildDeltaAnalyzer creates without errors."""
        from unittest.mock import MagicMock

        mock_cache = MagicMock()
        mock_cache.file_fingerprints = {}
        mock_cache.last_build = None
        mock_cache.config_hash = None
        mock_cache.parsed_content = {}

        analyzer = BuildDeltaAnalyzer(cache=mock_cache, root_path=test_site_root)

        assert analyzer.cache is mock_cache

    def test_dependency_visualizer_instantiation(self) -> None:
        """DependencyVisualizer creates without errors."""
        from unittest.mock import MagicMock

        mock_cache = MagicMock()
        mock_cache.file_fingerprints = {}
        mock_cache.dependencies = {}

        viz = DependencyVisualizer(cache=mock_cache)

        assert viz.cache is mock_cache

    def test_shortcode_sandbox_instantiation(self) -> None:
        """ShortcodeSandbox creates without errors."""
        sandbox = ShortcodeSandbox()

        # Should have inherited attributes from DebugTool
        assert hasattr(sandbox, "site")
        assert hasattr(sandbox, "cache")
        assert hasattr(sandbox, "root_path")


class TestDebugToolsAnalyze:
    """Verify debug tools' analyze() method works."""

    def test_content_migrator_analyze(self) -> None:
        """ContentMigrator.analyze() runs without error."""
        from unittest.mock import MagicMock

        mock_site = MagicMock()
        mock_site.pages = []

        migrator = ContentMigrator(site=mock_site)
        report = migrator.analyze()

        assert report.tool_name == "migrate"

    def test_incremental_debugger_analyze_without_cache(self) -> None:
        """IncrementalBuildDebugger.analyze() handles missing cache."""
        debugger = IncrementalBuildDebugger(cache=None)
        report = debugger.analyze()

        assert report.tool_name == "incremental"
        # Should have some findings even without cache

    def test_dependency_visualizer_analyze_without_cache(self) -> None:
        """DependencyVisualizer.analyze() handles missing cache."""
        viz = DependencyVisualizer(cache=None)
        report = viz.analyze()

        assert report.tool_name == "deps"

    def test_shortcode_sandbox_analyze(self) -> None:
        """ShortcodeSandbox.analyze() returns helpful message."""
        sandbox = ShortcodeSandbox()
        report = sandbox.analyze()

        assert report.tool_name == "sandbox"
        # Should indicate that content parameter is needed
        assert len(report.findings) > 0


class TestShortcodeSandboxRender:
    """Test ShortcodeSandbox rendering functionality."""

    def test_render_valid_directive(self) -> None:
        """Sandbox can render valid directives."""
        sandbox = ShortcodeSandbox()

        result = sandbox.render("```{note}\nThis is a note.\n```")

        # Should either succeed or fail gracefully
        assert result is not None
        assert hasattr(result, "success")
        assert hasattr(result, "html")

    def test_validate_known_directive(self) -> None:
        """Sandbox validates known directive names."""
        sandbox = ShortcodeSandbox()

        result = sandbox.validate("```{note}\nContent\n```")

        # 'note' is a known directive
        assert result.directive_name == "note"

    def test_validate_unknown_directive_suggests_alternatives(self) -> None:
        """Sandbox suggests alternatives for typos."""
        sandbox = ShortcodeSandbox()

        # 'notee' is a typo for 'note'
        result = sandbox.validate("```{notee}\nContent\n```")

        assert not result.valid
        assert "notee" in str(result.errors)
        # Should suggest 'note' as alternative
        if result.suggestions:
            assert any("note" in s for s in result.suggestions)


class TestConfigInspectorOperations:
    """Test ConfigInspector specific operations."""

    def test_get_nested_value(self) -> None:
        """ConfigInspector can extract nested config values."""
        from unittest.mock import MagicMock

        mock_site = MagicMock()
        mock_site.root_path = Path("/fake")

        inspector = ConfigInspector(site=mock_site)

        config = {
            "site": {
                "title": "Test",
                "nested": {"deep": "value"},
            },
        }

        assert inspector._get_nested_value(config, "site.title") == "Test"
        assert inspector._get_nested_value(config, "site.nested.deep") == "value"
        assert inspector._get_nested_value(config, "nonexistent") is None


class TestContentMigratorOperations:
    """Test ContentMigrator specific operations."""

    def test_path_to_url_conversion(self) -> None:
        """ContentMigrator converts file paths to URLs."""
        from unittest.mock import MagicMock

        mock_site = MagicMock()
        mock_site.pages = []

        migrator = ContentMigrator(site=mock_site)

        # Test various path formats
        assert migrator._path_to_url("content/docs/guide.md") == "/docs/guide"
        assert migrator._path_to_url("docs/guide.md") == "/docs/guide"
        assert migrator._path_to_url("content/docs/index.md") == "/docs"

    def test_slugify(self) -> None:
        """ContentMigrator slugifies headings correctly."""
        from unittest.mock import MagicMock

        mock_site = MagicMock()
        mock_site.pages = []

        migrator = ContentMigrator(site=mock_site)

        assert migrator._slugify("Hello World") == "hello-world"
        assert migrator._slugify("Some (Complex) Title!") == "some-complex-title"
        assert migrator._slugify("Multiple   Spaces") == "multiple-spaces"


class TestDependencyVisualizerOperations:
    """Test DependencyVisualizer specific operations."""

    def test_build_graph_from_cache(self) -> None:
        """DependencyVisualizer builds graph from cache data."""
        from unittest.mock import MagicMock

        mock_cache = MagicMock()
        mock_cache.file_fingerprints = {
            "content/page.md": "hash1",
            "templates/base.html": "hash2",
        }
        mock_cache.dependencies = {
            "content/page.md": {"templates/base.html"},
        }

        viz = DependencyVisualizer(cache=mock_cache)
        graph = viz.build_graph()

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert ("content/page.md", "templates/base.html") in graph.edges

    def test_blast_radius_calculation(self) -> None:
        """DependencyVisualizer calculates blast radius correctly."""
        from unittest.mock import MagicMock

        mock_cache = MagicMock()
        mock_cache.file_fingerprints = {
            "content/page1.md": "hash1",
            "content/page2.md": "hash2",
            "templates/base.html": "hash3",
        }
        mock_cache.dependencies = {
            "content/page1.md": {"templates/base.html"},
            "content/page2.md": {"templates/base.html"},
        }

        viz = DependencyVisualizer(cache=mock_cache)
        affected = viz.get_blast_radius("templates/base.html")

        # Both pages depend on base.html
        assert "content/page1.md" in affected
        assert "content/page2.md" in affected
