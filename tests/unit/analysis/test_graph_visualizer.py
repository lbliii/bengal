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
            "{{ graph_data_json }}",
        ]
        for var in required_vars:
            assert var in content, f"Template missing variable: {var}"

    def test_template_has_d3_script(self):
        """Template should include D3.js library."""
        content = _TEMPLATE_PATH.read_text(encoding="utf-8")
        assert "d3.v7" in content or "d3js.org" in content


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
        site.paths.asset_manifest = Path("/tmp/.bengal/asset-manifest.json")
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

    def test_context_has_graph_data_json(self, visualizer):
        """Context should include serialized graph data."""
        with patch.object(visualizer, "generate_graph_data") as mock_data:
            mock_data.return_value = {
                "stats": {},
                "nodes": [{"id": "1", "label": "Test"}],
                "edges": [],
            }
            context = visualizer._build_template_context()
            assert "graph_data_json" in context
            assert "Test" in context["graph_data_json"]


class TestRenderTemplate:
    """Test _render_template method."""

    @pytest.fixture
    def mock_site(self):
        """Create mock site for testing."""
        site = MagicMock()
        site.config = {"title": "Test Site", "baseurl": ""}
        site.output_dir = Path("/tmp/output")
        site.paths.asset_manifest = Path("/tmp/.bengal/asset-manifest.json")
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
            "graph_data_json": '{"nodes": []}',
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
            "graph_data_json": "{}",
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
            "graph_data_json": '{"nodes":[],"edges":[]}',
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
        site.paths.asset_manifest = Path("/tmp/.bengal/asset-manifest.json")
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

    def test_generate_html_includes_graph_data(self, visualizer):
        """generate_html should embed graph data in output."""
        with patch.object(visualizer, "generate_graph_data") as mock_data:
            mock_data.return_value = {
                "stats": {"total_pages": 5, "total_links": 8, "hubs": 1, "orphans": 2},
                "nodes": [{"id": "test-page", "label": "Test Page"}],
                "edges": [],
            }
            html = visualizer.generate_html()
            assert "test-page" in html
            assert "Test Page" in html

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
