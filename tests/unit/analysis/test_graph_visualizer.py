"""Tests for graph visualizer template extraction.

Verifies that the template-based HTML generation (RFC: rfc-code-smell-remediation.md §1.3)
produces correct output.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bengal.analysis.graph.visualizer import _TEMPLATE_PATH, GraphVisualizer


class TestTemplateExists:
    """Verify template file exists and is valid."""

    def test_template_path_exists(self):
        """Template file should exist at expected path."""
        assert _TEMPLATE_PATH.exists(), f"Template not found at {_TEMPLATE_PATH}"

    def test_template_is_html(self):
        """Template should be valid HTML structure."""
        content = _TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "</html>" in content
        assert "<body" in content
        assert "</body>" in content

    def test_template_has_required_variables(self):
        """Template should contain all required mustache variables."""
        content = _TEMPLATE_PATH.read_text(encoding="utf-8")
        required_vars = [
            "{{ title }}",
            "{{ css_path }}",
            "{{ default_appearance }}",
            "{{ default_palette }}",
            "{{ stats.total_pages }}",
            "{{ stats.total_links }}",
            "{{ stats.hubs }}",
            "{{ stats.orphans }}",
            "{{ graph_json_url }}",
        ]
        for var in required_vars:
            assert var in content, f"Template missing variable: {var}"

    def test_template_has_no_d3_and_mounts_explorer(self):
        """Template must not load D3 from any CDN (zero external requests) and
        should mount the dependency-free canvas explorer instead."""
        content = _TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "d3.v7" not in content
        assert "d3js.org" not in content
        assert "explorer_js_path" in content  # mounts the canvas explorer at render
        assert "BENGAL_GRAPH_JSON_URL" in content

    def test_template_has_tag_filter_markup(self):
        """Template should carry the ?tag= filter UI (logic lives in the JS)."""
        content = _TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "tag-filter-badge" in content
        assert "tag-filter-value" in content

    def test_explorer_js_has_tag_filter_logic(self):
        """The canvas explorer should implement the ?tag= filtering behavior."""
        explorer = (
            Path(__file__).resolve().parents[3]
            / "bengal/themes/default/assets/js/bengal-graph-explorer.js"
        )
        content = explorer.read_text(encoding="utf-8")
        assert "tagParam" in content
        assert "nodeMatchesTag" in content
        assert "resolveCssColor" in content
        assert "nodeScreenRadius" in content
        assert "buildLabelHubs" in content
        # No D3 API usage (comments may mention D3, but nothing should call it).
        assert "d3.forceSimulation" not in content
        assert "d3.select" not in content


class TestBuildTemplateContext:
    """Test _build_template_context method."""

    @pytest.fixture
    def mock_site(self):
        """Create mock site for testing."""
        site = MagicMock()
        site.config = {"title": "Test Site", "baseurl": "/test"}
        site.baseurl = "/test"
        site.title = "Test Site"
        site.output_dir = Path("/tmp/output")
        site.config_service.paths.asset_manifest = Path("/tmp/.bengal/asset-manifest.json")
        site.theme = None
        return site

    @pytest.fixture
    def mock_graph(self):
        """Create mock knowledge graph."""
        graph = MagicMock()
        return graph

    @pytest.fixture
    def visualizer(self, mock_site, mock_graph):
        """Create visualizer instance."""
        return GraphVisualizer(mock_site, mock_graph)

    def test_context_has_title(self, visualizer):
        """Context should include title."""
        with patch.object(visualizer, "generate_graph_data") as mock_data:
            mock_data.return_value = {"stats": {}, "nodes": [], "edges": []}
            context = visualizer._build_template_context("Custom Title")
            assert context["title"] == "Custom Title"

    def test_context_default_title(self, visualizer):
        """Context should use default title from site config."""
        with patch.object(visualizer, "generate_graph_data") as mock_data:
            mock_data.return_value = {"stats": {}, "nodes": [], "edges": []}
            context = visualizer._build_template_context(None)
            assert "Test Site" in context["title"]
            assert "Knowledge Graph" in context["title"]

    def test_context_has_css_path(self, visualizer):
        """Context should include CSS path with baseurl."""
        with patch.object(visualizer, "generate_graph_data") as mock_data:
            mock_data.return_value = {"stats": {}, "nodes": [], "edges": []}
            context = visualizer._build_template_context()
            assert "/test/assets/css/style.css" in context["css_path"]

    def test_context_has_stats(self, visualizer):
        """Context should include graph stats."""
        with patch.object(visualizer, "generate_graph_data") as mock_data:
            mock_data.return_value = {
                "stats": {"total_pages": 10, "total_links": 20, "hubs": 2, "orphans": 3},
                "nodes": [],
                "edges": [],
            }
            context = visualizer._build_template_context()
            assert context["stats"]["total_pages"] == 10
            assert context["stats"]["total_links"] == 20
            assert context["stats"]["hubs"] == 2
            assert context["stats"]["orphans"] == 3

    def test_context_has_graph_json_url(self, visualizer):
        """Context should include graph.json URL for fetch."""
        with patch.object(visualizer, "generate_graph_data") as mock_data:
            mock_data.return_value = {
                "stats": {},
                "nodes": [{"id": "1", "label": "Test"}],
                "edges": [],
            }
            context = visualizer._build_template_context()
            assert "graph_json_url" in context
            assert context["graph_json_url"] == "graph.json"


class TestRenderTemplate:
    """Test _render_template method."""

    @pytest.fixture
    def mock_site(self):
        """Create mock site for testing."""
        site = MagicMock()
        site.config = {"title": "Test Site", "baseurl": ""}
        site.output_dir = Path("/tmp/output")
        site.config_service.paths.asset_manifest = Path("/tmp/.bengal/asset-manifest.json")
        site.theme = None
        return site

    @pytest.fixture
    def mock_graph(self):
        """Create mock knowledge graph."""
        graph = MagicMock()
        return graph

    @pytest.fixture
    def visualizer(self, mock_site, mock_graph):
        """Create visualizer instance."""
        return GraphVisualizer(mock_site, mock_graph)

    def test_render_replaces_simple_variables(self, visualizer):
        """Template rendering should replace simple variables."""
        context = {
            "title": "My Graph",
            "css_path": "/css/style.css",
            "default_appearance": "dark",
            "default_palette": "ocean",
            "stats": {"total_pages": 5, "total_links": 10, "hubs": 1, "orphans": 2},
            "graph_json_url": "graph.json",
        }
        html = visualizer._render_template(context)

        assert "My Graph" in html
        assert "/css/style.css" in html
        assert "dark" in html
        assert "ocean" in html

    def test_render_replaces_nested_variables(self, visualizer):
        """Template rendering should replace nested dict variables."""
        context = {
            "title": "Test",
            "css_path": "/test.css",
            "default_appearance": "light",
            "default_palette": "",
            "stats": {"total_pages": 42, "total_links": 100, "hubs": 5, "orphans": 10},
            "graph_json_url": "graph.json",
        }
        html = visualizer._render_template(context)

        # Check nested variable replacement
        assert "42" in html  # stats.total_pages
        assert "100" in html  # stats.total_links

    def test_render_produces_valid_html(self, visualizer):
        """Rendered output should be valid HTML."""
        context = {
            "title": "Test",
            "css_path": "/test.css",
            "default_appearance": "system",
            "default_palette": "",
            "stats": {"total_pages": 1, "total_links": 0, "hubs": 0, "orphans": 0},
            "graph_json_url": "graph.json",
        }
        html = visualizer._render_template(context)

        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert "{{ " not in html  # No unreplaced variables


class TestGenerateHtml:
    """Test the main generate_html method."""

    @pytest.fixture
    def mock_site(self):
        """Create mock site for testing."""
        site = MagicMock()
        site.config = {"title": "Test Site", "baseurl": ""}
        site.output_dir = Path("/tmp/output")
        site.config_service.paths.asset_manifest = Path("/tmp/.bengal/asset-manifest.json")
        site.theme = None
        return site

    @pytest.fixture
    def mock_graph(self):
        """Create mock knowledge graph."""
        graph = MagicMock()
        return graph

    @pytest.fixture
    def visualizer(self, mock_site, mock_graph):
        """Create visualizer instance."""
        return GraphVisualizer(mock_site, mock_graph)

    def test_generate_html_returns_string(self, visualizer):
        """generate_html should return a string."""
        with patch.object(visualizer, "generate_graph_data") as mock_data:
            mock_data.return_value = {
                "stats": {"total_pages": 0, "total_links": 0, "hubs": 0, "orphans": 0},
                "nodes": [],
                "edges": [],
            }
            result = visualizer.generate_html()
            assert isinstance(result, str)

    def test_generate_html_includes_graph_json_url(self, visualizer):
        """generate_html should include graph.json URL for client-side fetch."""
        with patch.object(visualizer, "generate_graph_data") as mock_data:
            mock_data.return_value = {
                "stats": {"total_pages": 5, "total_links": 8, "hubs": 1, "orphans": 2},
                "nodes": [{"id": "test-page", "label": "Test Page"}],
                "edges": [],
            }
            html = visualizer.generate_html()
            assert "graph.json" in html
            assert "BENGAL_GRAPH_JSON_URL" in html
            assert "bengal-graph-explorer" in html

    def test_generate_html_uses_custom_title(self, visualizer):
        """generate_html should use custom title when provided."""
        with patch.object(visualizer, "generate_graph_data") as mock_data:
            mock_data.return_value = {
                "stats": {"total_pages": 0, "total_links": 0, "hubs": 0, "orphans": 0},
                "nodes": [],
                "edges": [],
            }
            html = visualizer.generate_html(title="My Custom Graph")
            assert "My Custom Graph" in html
